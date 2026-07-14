# -*- coding: utf-8 -*-
import os
import time
from pathlib import Path


# 当前脚本所在的文件夹。jkrc.pyd 和 jakaAPI.dll 也在这个文件夹里。
SDK_DIR = Path(__file__).resolve().parent

# 机器人/虚拟机 IP 地址。如果你的虚拟机 IP 变化，只需要改这里。
ROBOT_IP = "192.168.56.105"


def check_result(action_name, result):
    """检查 SDK 函数返回值。返回码为 0 表示成功。"""
    print(f"{action_name}: {result}")

    if not result or result[0] != 0:
        raise RuntimeError(f"{action_name} failed, return={result}")


def main():
    """程序入口：连接机器人，完成上电/上使能/下使能/下电。"""

    # Windows 下显式加入 DLL 搜索路径，帮助 Python 找到 jakaAPI.dll。
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(SDK_DIR))

    # 导入 JAKA Python SDK。
    import jkrc

    # 创建机器人控制对象。这里还不算真正登录，只是告诉 SDK 要连接哪个 IP。
    robot = jkrc.RC(ROBOT_IP)

    # 记录是否已经登录。这样即使中途报错，也可以在 finally 里安全登出。
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

        # 4. 下使能。机器人退出可运动状态。
        check_result("disable_robot", robot.disable_robot())
        time.sleep(1)

        # 5. 下电。
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
