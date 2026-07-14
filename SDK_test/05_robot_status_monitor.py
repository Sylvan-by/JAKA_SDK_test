# -*- coding: utf-8 -*-
import math
import os
import time
from pathlib import Path


# 当前脚本所在的文件夹。jkrc.pyd 和 jakaAPI.dll 也在这个文件夹里。
SDK_DIR = Path(__file__).resolve().parent

# 机器人/虚拟机 IP 地址。如果虚拟机 IP 变化，只需要修改这里。
ROBOT_IP = "192.168.56.105"

# 运动模式：0 表示绝对运动，1 表示增量运动。
ABS = 0

# 本节仍然使用前面熟悉的 home 点。
# 为了方便阅读，这里使用角度；发送给 SDK 前再转换成弧度。
HOME_JOINT_DEG = [0, 90, 90, 90, -90, 0]

# joint_move 的速度单位是 rad/s。
JOINT_SPEED_RAD_S = 0.2


def check_result(action_name, result):
    """检查只需要判断成功或失败的 SDK 返回值。"""
    print(f"{action_name}: {result}")

    # SDK 返回值通常是元组，第 1 个元素 result[0] 是接口返回码。
    # 返回码为 0 表示这次 SDK 接口调用成功。
    if not result or result[0] != 0:
        raise RuntimeError(f"{action_name} failed, return={result}")


def get_data(action_name, result):
    """检查查询接口，并取出返回值中的数据部分。"""
    print(f"{action_name} raw return: {result}")

    if not result or result[0] != 0:
        raise RuntimeError(f"{action_name} failed, return={result}")

    # 查询接口成功时通常返回 (0, data)：
    # result[0] 是接口返回码，result[1] 才是我们需要的数据。
    if len(result) < 2:
        raise RuntimeError(f"{action_name} returned no data: {result}")

    return result[1]


def deg_to_rad_list(degrees):
    """把一组角度值转换成 SDK 需要的弧度值。"""
    return [math.radians(value) for value in degrees]


def rad_to_deg_list(radians):
    """把 SDK 返回的弧度值转换成更方便观察的角度值。"""
    return [math.degrees(value) for value in radians]


def round_list(values, digits=3):
    """限制小数位数，让终端输出更容易阅读。"""
    return [round(value, digits) for value in values]


def show_joint_positions(robot, title):
    """读取并显示普通关节位置和伺服反馈关节位置。"""
    print(f"\n--- {title}: joint positions ---")

    # get_joint_position()：读取 SDK 当前关节位置。
    joint_rad = get_data("get_joint_position", robot.get_joint_position())
    joint_deg = rad_to_deg_list(joint_rad)
    print("joint position (deg):", round_list(joint_deg))

    # get_actual_joint_position()：读取伺服反馈的实际关节位置。
    # 在机器人停止后，两组值通常非常接近，但可能存在微小误差。
    actual_joint_rad = get_data(
        "get_actual_joint_position",
        robot.get_actual_joint_position(),
    )
    actual_joint_deg = rad_to_deg_list(actual_joint_rad)
    print("actual joint position (deg):", round_list(actual_joint_deg))

    return actual_joint_deg


def show_tcp_positions(robot, title):
    """读取并显示普通 TCP 位姿和伺服反馈 TCP 位姿。"""
    print(f"\n--- {title}: TCP positions ---")

    tcp_pose = get_data("get_tcp_position", robot.get_tcp_position())
    actual_tcp_pose = get_data(
        "get_actual_tcp_position",
        robot.get_actual_tcp_position(),
    )

    # TCP 位姿的前 3 个值是 x、y、z，单位为 mm；
    # 后 3 个值是 rx、ry、rz，单位为 rad，所以转换成 degree 后显示。
    tcp_for_display = list(tcp_pose[:3]) + rad_to_deg_list(tcp_pose[3:])
    actual_tcp_for_display = list(actual_tcp_pose[:3]) + rad_to_deg_list(
        actual_tcp_pose[3:]
    )

    print("TCP [x, y, z, rx, ry, rz] (mm/deg):", round_list(tcp_for_display))
    print(
        "actual TCP [x, y, z, rx, ry, rz] (mm/deg):",
        round_list(actual_tcp_for_display),
    )


def show_robot_status(robot, title):
    """读取机器人基本状态、运动状态和最后一个机器人错误。"""
    print(f"\n--- {title}: robot status ---")

    # simple 状态中主要包含：机器人错误、上电状态和使能状态。
    # 不同 SDK 小版本的数据表现形式可能是元组、列表或其他结构，
    # 因此本节先完整打印原始数据，熟悉 SDK 实际返回的内容。
    simple_status = get_data(
        "get_robot_status_simple",
        robot.get_robot_status_simple(),
    )
    print("simple status data:", simple_status)

    # 运动状态中可以观察是否到位、是否暂停、运动队列以及限位等信息。
    motion_status = get_data("get_motion_status", robot.get_motion_status())
    print("motion status data:", motion_status)

    # is_in_pos() 返回的 data 为 1 表示机器人已经停止并到位，为 0 表示未到位。
    in_pos = get_data("is_in_pos", robot.is_in_pos())
    print("robot is in position:", bool(in_pos))

    # 注意这里有两层“错误码”：
    # get_last_error() 返回值中的第一个 0，表示查询接口调用成功；
    # 第二个数据才是机器人运行过程中记录的最后一个错误。
    last_error = get_data("get_last_error", robot.get_last_error())
    print("robot last error:", last_error)


def compare_with_home(actual_joint_deg):
    """比较机器人实际关节位置与 home 目标值之间的误差。"""
    errors = [
        actual - target
        for actual, target in zip(actual_joint_deg, HOME_JOINT_DEG)
    ]
    print("home target (deg):", HOME_JOINT_DEG)
    print("actual - target (deg):", round_list(errors))


def main():
    """登录机器人，运动到 home 点，并在关键节点读取机器人状态。"""

    # Windows 下显式加入 DLL 搜索路径，帮助 Python 找到 jakaAPI.dll。
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(SDK_DIR))

    # DLL 搜索路径准备好以后，再导入 JAKA Python SDK。
    import jkrc

    # 创建机器人控制对象。这里只指定控制器 IP，还没有真正登录。
    robot = jkrc.RC(ROBOT_IP)

    # 这三个变量是程序自己记录的状态，用于 finally 中进行清理。
    logged_in = False
    powered_on = False
    enabled = False

    try:
        # 1. 登录控制器。
        check_result("login", robot.login())
        logged_in = True

        # 2. 查询 SDK 版本。它也是典型的 (返回码, 数据) 查询接口。
        sdk_version = get_data("get_sdk_version", robot.get_sdk_version())
        print("SDK version:", sdk_version)

        # 3. 上电并等待 1 秒。
        check_result("power_on", robot.power_on())
        powered_on = True
        time.sleep(1)

        # 4. 上使能并等待 1 秒。
        check_result("enable_robot", robot.enable_robot())
        enabled = True
        time.sleep(1)

        # 5. 在运动前读取一次状态和当前位置，作为初始数据。
        show_robot_status(robot, "before motion")
        show_joint_positions(robot, "before motion")
        show_tcp_positions(robot, "before motion")

        # 6. 关节绝对运动到 home 点。
        # True 表示阻塞运动：机器人运动完成后，joint_move() 才返回。
        home_joint_rad = deg_to_rad_list(HOME_JOINT_DEG)
        check_result(
            "joint_move ABS home",
            robot.joint_move(home_joint_rad, ABS, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 7. 运动完成后再次读取状态和位置。
        show_robot_status(robot, "after home motion")
        actual_joint_deg = show_joint_positions(robot, "after home motion")
        show_tcp_positions(robot, "after home motion")

        # 8. 将实际关节位置与 home 目标进行比较。
        compare_with_home(actual_joint_deg)

        # 9. 下使能。
        check_result("disable_robot", robot.disable_robot())
        enabled = False
        time.sleep(1)

        # 10. 下电。
        check_result("power_off", robot.power_off())
        powered_on = False
        time.sleep(1)

    finally:
        # 如果中途发生异常，尽量按照“下使能 -> 下电 -> 登出”的顺序清理。
        if logged_in:
            if enabled:
                print("cleanup disable_robot:", robot.disable_robot())
            if powered_on:
                print("cleanup power_off:", robot.power_off())
            print("logout:", robot.logout())


# 只有直接运行本文件时才执行 main()。
# 如果以后被其他 Python 文件 import，则不会自动控制机器人。
if __name__ == "__main__":
    main()
