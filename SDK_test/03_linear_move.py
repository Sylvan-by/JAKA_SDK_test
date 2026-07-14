# -*- coding: utf-8 -*-
import math
import os
import time
from pathlib import Path


# 当前脚本所在的文件夹。jkrc.pyd 和 jakaAPI.dll 也在这个文件夹里。
SDK_DIR = Path(__file__).resolve().parent

# 机器人/虚拟机 IP 地址。如果你的虚拟机 IP 变化，只需要改这里。
ROBOT_IP = "192.168.56.105"

# SDK 里的运动模式：
# ABS  = 0：绝对运动，目标值就是机器人要到达的位置。
# INCR = 1：增量运动，目标值是在当前位置基础上增加/减少的量。
ABS = 0
INCR = 1

# home 关节位置。为了方便阅读，这里用角度写，调用 SDK 前会转换成弧度。
HOME_JOINT_DEG = [0, 90, 90, 90, -90, 0]

# 直线绝对运动目标点。
# linear_move 的 TCP 位置单位是 mm，姿态 rx/ry/rz 单位是 rad。
# 所以这里把姿态先用角度写，调用 SDK 前再转换成弧度。
TARGET_TCP_POS_MM = [-1000, 500, 1000]
TARGET_TCP_ORI_DEG = [180, 0, 90]

# 直线增量运动：沿当前默认坐标系 X 轴正方向移动 300 mm，姿态不变。
X_FORWARD_300MM = [300, 0, 0, 0, 0, 0]

# 运动速度。
# joint_move 的速度单位是 rad/s。
# linear_move 的速度单位是 mm/s。
JOINT_SPEED_RAD_S = 0.4
LINEAR_SPEED_MM_S = 50


def check_result(action_name, result):
    """检查 SDK 函数返回值。返回码为 0 表示成功。"""
    print(f"{action_name}: {result}")

    if not result or result[0] != 0:
        raise RuntimeError(f"{action_name} failed, return={result}")


def deg_to_rad_list(degrees):
    """把一组角度值转换成 SDK 需要的弧度值。"""
    return [math.radians(value) for value in degrees]


def make_tcp_pose(position_mm, orientation_deg):
    """把 [x, y, z] mm 和 [rx, ry, rz] degree 组合成 SDK 需要的 TCP 位姿。"""
    return list(position_mm) + deg_to_rad_list(orientation_deg)


def main():
    """程序入口：home -> 直线绝对运动 -> 直线增量运动 -> 回 home。"""

    # Windows 下显式加入 DLL 搜索路径，帮助 Python 找到 jakaAPI.dll。
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(SDK_DIR))

    # 导入 JAKA Python SDK。
    import jkrc

    # 创建机器人控制对象。这里还不算真正登录，只是告诉 SDK 要连接哪个 IP。
    robot = jkrc.RC(ROBOT_IP)
    logged_in = False

    try:
        # 1. 登录机器人控制器。
        check_result("login", robot.login())
        logged_in = True

        # 2. 上电。虚拟机响应较快，这里只等待 1 秒。
        check_result("power_on", robot.power_on())
        time.sleep(1)

        # 3. 上使能。上使能后机器人才能执行运动指令。
        check_result("enable_robot", robot.enable_robot())
        time.sleep(1)

        # 4. 先关节绝对运动到 home 点：
        #    (0, 90, 90, 90, -90, 0) degree。
        home_joint_rad = deg_to_rad_list(HOME_JOINT_DEG)
        print("home joint deg:", HOME_JOINT_DEG)
        print("home joint rad:", home_joint_rad)
        check_result(
            "joint_move ABS home",
            robot.joint_move(home_joint_rad, ABS, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 5. 直线绝对运动到指定 TCP 点：
        #    (-1000, 500, 1000, 180, 0, 90)
        #    前三个数是 mm，后三个数是 degree。
        target_tcp = make_tcp_pose(TARGET_TCP_POS_MM, TARGET_TCP_ORI_DEG)
        print("target tcp pos mm:", TARGET_TCP_POS_MM)
        print("target tcp ori deg:", TARGET_TCP_ORI_DEG)
        print("target tcp sdk pose:", target_tcp)
        check_result(
            "linear_move ABS target",
            robot.linear_move(target_tcp, ABS, True, LINEAR_SPEED_MM_S),
        )
        time.sleep(1)

        # 6. 读取当前 TCP，方便观察 X 正方向增量运动前的位置。
        ret = robot.get_tcp_position()
        check_result("get_tcp_position before X+300", ret)
        print("tcp before X+300:", ret[1])

        # 7. 直线增量运动：在当前位置基础上，沿 X 轴正方向移动 300 mm。
        check_result(
            "linear_move INCR X+300mm",
            robot.linear_move(X_FORWARD_300MM, INCR, True, LINEAR_SPEED_MM_S),
        )
        time.sleep(1)

        # 8. 再读取一次 TCP，理论上 X 值会比运动前增加约 300 mm。
        ret = robot.get_tcp_position()
        check_result("get_tcp_position after X+300", ret)
        print("tcp after X+300:", ret[1])

        # 9. 最后再关节绝对运动回 home 点。
        check_result(
            "joint_move ABS home again",
            robot.joint_move(home_joint_rad, ABS, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 10. 下使能。
        check_result("disable_robot", robot.disable_robot())
        time.sleep(1)

        # 11. 下电。
        check_result("power_off", robot.power_off())
        time.sleep(1)

    finally:
        # 无论前面成功还是报错，只要登录过，就尝试登出。
        if logged_in:
            print("logout:", robot.logout())


# 只有直接运行这个文件时，才执行 main()。
# 如果以后这个文件被其他 Python 文件 import，则不会自动执行。
if __name__ == "__main__":
    main()
