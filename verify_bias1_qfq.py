"""
Bias1 Qfq 因子验证 - 快速启动脚本

使用方法:
    python verify_bias1_qfq.py

或者指定参数:
    python verify_bias1_qfq.py --start_date 20240101 --end_date 20240630
"""

import subprocess
import sys

def main():
    print("=" * 80)
    print("Bias1 Qfq 因子验证启动器")
    print("=" * 80)

    # 检查参数
    if len(sys.argv) > 1:
        # 使用命令行参数
        cmd = [sys.executable, '/home/zcy/alpha因子库/scripts/test/verify_bias1_qfq.py'] + sys.argv[1:]
    else:
        # 使用默认参数
        print("\n使用默认参数:")
        print("  开始日期: 20240101")
        print("  结束日期: 20241231")
        print("\n如需自定义参数，请使用:")
        print("  python verify_bias1_qfq.py --start_date 20240101 --end_date 20240630")
        print("\n开始执行...\n")

        cmd = [
            sys.executable,
            '/home/zcy/alpha因子库/scripts/test/verify_bias1_qfq.py',
            '--start_date', '20240101',
            '--end_date', '20241231'
        ]

    # 执行验证
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n验证执行失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断执行")
        sys.exit(0)


if __name__ == "__main__":
    main()
