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
# ABS  = 0：绝对运动，目标值就是机器人要到达的关节位置。
# INCR = 1：增量运动，目标值是在当前位置基础上增加/减少的量。
ABS = 0
INCR = 1

# 关节目标位置。为了方便阅读，这里用角度写，调用 SDK 前会转换成弧度。
HOME_JOINT_DEG = [0, 90, 90, 90, -90, 0]

# 在 HOME_JOINT_DEG 的基础上，让 1 关节正向/反向各运动 30 度。
JOINT1_STEP_DEG = 30

# joint_move 的速度单位是 rad/s。测试时建议先使用较低速度。
JOINT_SPEED_RAD_S = 0.2


def check_result(action_name, result):
    """检查 SDK 函数返回值。返回码为 0 表示成功。"""
    print(f"{action_name}: {result}")

    if not result or result[0] != 0:
        raise RuntimeError(f"{action_name} failed, return={result}")


def deg_to_rad_list(degrees):
    """把一组角度值转换成 SDK 需要的弧度值。"""
    return [math.radians(value) for value in degrees]


def main():
    """程序入口：上电上使能后，执行一次绝对关节运动和两次增量关节运动。"""

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

        # 4. 绝对关节运动到指定位置：
        #    (0, 90, 90, 90, -90, 0) degree。
        home_joint_rad = deg_to_rad_list(HOME_JOINT_DEG)
        print("home joint deg:", HOME_JOINT_DEG)
        print("home joint rad:", home_joint_rad)
        check_result(
            "joint_move ABS home",
            robot.joint_move(home_joint_rad, ABS, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 5. 增量运动：在当前位置基础上，让 1 关节正向运动 30 度。
        joint1_forward_rad = deg_to_rad_list([JOINT1_STEP_DEG, 0, 0, 0, 0, 0])
        check_result(
            "joint_move INCR J1 +30deg",
            robot.joint_move(joint1_forward_rad, INCR, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 6. 增量运动：在当前位置基础上，让 1 关节反向运动 30 度，回到原位置。
        joint1_backward_rad = deg_to_rad_list([-JOINT1_STEP_DEG, 0, 0, 0, 0, 0])
        check_result(
            "joint_move INCR J1 -30deg",
            robot.joint_move(joint1_backward_rad, INCR, True, JOINT_SPEED_RAD_S),
        )
        time.sleep(1)

        # 7. 下使能。
        check_result("disable_robot", robot.disable_robot())
        time.sleep(1)

        # 8. 下电。
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
