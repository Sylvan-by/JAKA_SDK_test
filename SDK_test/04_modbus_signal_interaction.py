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

# IO 类型。
# Python SDK 文档里的普通 IO 示例常见是：
# IO_CABINET = 0：控制柜 IO
# IO_TOOL    = 1：工具 IO
# IO_EXTEND  = 2：扩展 IO
#
# TCP/IP 文档里还列出了：
# IO_MODBUS  = 4：Modbus IO
#
# 这次你说信号交互全部走 Modbus，所以 DO/DI 都使用 IO_MODBUS。
IO_CABINET = 0
IO_TOOL = 1
IO_EXTEND = 2
IO_MODBUS = 4

MODBUS_DO_TYPE = IO_MODBUS
MODBUS_DI_TYPE = IO_MODBUS

# Python SDK 文档写的是：IO 索引从 0 开始。
# 所以现场习惯说的 DO_1 / DI_1，在 Python SDK 里通常对应 index = 0。
#
# 注意：TCP/IP 原始协议文档里 index=1 表示第 1 个 DO，
# 但 Python SDK 文档明确写 index 从 0 开始。这里按 Python SDK 写。
DO_1_INDEX = 0
DI_1_INDEX = 0

# 等待 DI_1 的轮询周期。每 1 秒读一次 DI 状态。
DI_POLL_INTERVAL_S = 1

# 是否在正式运动前先做 IO 预检查。
# 如果 IO 类型/索引配置不对，程序会在机器人运动前就停下来。
PRECHECK_IO_BEFORE_MOTION = True

# home 关节位置。为了方便阅读，这里用角度写，调用 SDK 前会转换成弧度。
HOME_JOINT_DEG = [0, 90, 90, 90, -90, 0]

# 相对直线运动：
# linear_move 的 TCP 位置单位是 mm，姿态 rx/ry/rz 单位是 rad。
Z_DOWN_200MM = [0, 0, -200, 0, 0, 0]
X_FORWARD_200MM = [200, 0, 0, 0, 0, 0]

# 单关节增量运动：1 关节正向移动 30 度。
JOINT1_FORWARD_30DEG = [30, 0, 0, 0, 0, 0]

# 运动速度。
# joint_move 的速度单位是 rad/s。
# linear_move 的速度单位是 mm/s。
JOINT_SPEED_RAD_S = 0.2
LINEAR_SPEED_MM_S = 50


def check_result(action_name, result):
    """检查 SDK 函数返回值。返回码为 0 表示成功。"""
    print(f"{action_name}: {result}")

    if not result or result[0] != 0:
        raise RuntimeError(f"{action_name} failed, return={result}")


def deg_to_rad_list(degrees):
    """把一组角度值转换成 SDK 需要的弧度值。"""
    return [math.radians(value) for value in degrees]


def set_do(robot, index, value):
    """设置数字输出 DO。value=True 表示打开，False 表示关闭。"""
    check_result(
        f"set DO type={MODBUS_DO_TYPE} index={index} value={value}",
        robot.set_digital_output(MODBUS_DO_TYPE, index, value),
    )


def get_di(robot, index):
    """读取数字输入 DI，返回 True/False。"""
    ret = robot.get_digital_input(MODBUS_DI_TYPE, index)
    check_result(f"read DI type={MODBUS_DI_TYPE} index={index}", ret)
    return ret[1]


def precheck_io(robot):
    """正式运动前检查 DO/DI 接口是否能通过当前 IO 类型访问。"""
    print("precheck IO start")
    print(
        f"MODBUS_DO_TYPE={MODBUS_DO_TYPE}, MODBUS_DI_TYPE={MODBUS_DI_TYPE}, "
        f"DO_1_INDEX={DO_1_INDEX}, DI_1_INDEX={DI_1_INDEX}"
    )

    di_value = get_di(robot, DI_1_INDEX)
    print(f"DI_1 current value: {di_value}")

    # 预检查阶段只把 DO_1 关一次，确认 DO 接口可写。
    set_do(robot, DO_1_INDEX, False)
    print("precheck IO done")


def wait_di_on(robot, index):
    """一直等待指定 DI 变为开。"""
    print(f"waiting DI type={MODBUS_DI_TYPE} index={index} ON ...")

    while True:
        di_value = get_di(robot, index)
        print(f"DI type={MODBUS_DI_TYPE} index={index} value={di_value}")

        if di_value:
            print(f"DI type={MODBUS_DI_TYPE} index={index} is ON, continue.")
            return

        time.sleep(DI_POLL_INTERVAL_S)


def main():
    """程序入口：运动流程中打开/关闭 DO，并等待 DI 输入。"""

    # Windows 下显式加入 DLL 搜索路径，帮助 Python 找到 jakaAPI.dll。
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(SDK_DIR))

    # 导入 JAKA Python SDK。
    import jkrc

    # 创建机器人控制对象。这里还不算真正登录，只是告诉 SDK 要连接哪个 IP。
    robot = jkrc.RC(ROBOT_IP)
    logged_in = False
    powered_on = False
    enabled = False

    try:
        # 1. 登录机器人控制器。
        check_result("login", robot.login())
        logged_in = True

        # 2. 上电。虚拟机响应较快，这里只等待 1 秒。
        check_result("power_on", robot.power_on())
        powered_on = True
        time.sleep(1)

        # 3. 上使能。上使能后机器人才能执行运动指令。
        check_result("enable_robot", robot.enable_robot())
        enabled = True
        time.sleep(1)

        if PRECHECK_IO_BEFORE_MOTION:
            precheck_io(robot)
            time.sleep(1)

        # 4. 关节绝对运动到 home 点：
        #    (0, 90, 90, 90, -90, 0) degree。
        home_joint_rad = deg_to_rad_list(HOME_JOINT_DEG)
        check_result(
            "joint_move ABS home",
            robot.joint_move(home_joint_rad, ABS, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 5. 相对直线运动：Z 轴负方向移动 200 mm。
        check_result(
            "linear_move INCR Z-200mm",
            robot.linear_move(Z_DOWN_200MM, INCR, True, LINEAR_SPEED_MM_S),
        )
        time.sleep(1)

        # 6. 打开 DO_1。
        set_do(robot, DO_1_INDEX, True)
        time.sleep(1)

        # 7. 相对直线运动：X 轴正方向移动 200 mm。
        check_result(
            "linear_move INCR X+200mm",
            robot.linear_move(X_FORWARD_200MM, INCR, True, LINEAR_SPEED_MM_S),
        )
        time.sleep(1)

        # 8. 单关节增量运动：1 关节正向移动 30 度。
        check_result(
            "joint_move INCR J1 +30deg",
            robot.joint_move(
                deg_to_rad_list(JOINT1_FORWARD_30DEG),
                INCR,
                True,
                JOINT_SPEED_RAD_S,
            ),
        )
        time.sleep(1)

        # 9. 等待 DI_1 为开。你可以用 Modbus Poll 模拟这个输入。
        wait_di_on(robot, DI_1_INDEX)

        # 10. DI_1 变为开后，关节绝对运动回 home 点。
        check_result(
            "joint_move ABS home again",
            robot.joint_move(home_joint_rad, ABS, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 11. 回到 home 点后再关闭 DO_1，方便观察 DO 保持打开的状态。
        set_do(robot, DO_1_INDEX, False)
        time.sleep(1)

        # 12. 下使能。
        check_result("disable_robot", robot.disable_robot())
        enabled = False
        time.sleep(1)

        # 13. 下电。
        check_result("power_off", robot.power_off())
        powered_on = False
        time.sleep(1)

    finally:
        # 无论前面成功还是报错，只要登录过，就尽量下使能、下电、登出。
        if logged_in:
            if enabled:
                print("cleanup disable_robot:", robot.disable_robot())
            if powered_on:
                print("cleanup power_off:", robot.power_off())
            print("logout:", robot.logout())


# 只有直接运行这个文件时，才执行 main()。
# 如果以后这个文件被其他 Python 文件 import，则不会自动执行。
if __name__ == "__main__":
    main()
