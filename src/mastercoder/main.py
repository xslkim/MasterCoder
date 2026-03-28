"""MasterCoder 主入口 - 交互式 REPL。"""

import sys


def main() -> None:
    """主函数 - 启动 REPL 循环。"""
    print("MasterCoder v0.1.0")
    print("Type /help for available commands, /exit to quit.")
    
    try:
        while True:
            try:
                # 显示提示符并读取用户输入
                user_input = input("> ")
                
                # 空行跳过
                if not user_input.strip():
                    continue
                
                # /exit 命令退出
                if user_input.strip() == "/exit":
                    print("Goodbye!")
                    sys.exit(0)
                
                # 暂时原样回显（后续需求接入 AI）
                print(user_input)
                
            except KeyboardInterrupt:
                # Ctrl+C 处理
                print("\nGoodbye!")
                sys.exit(0)
    except EOFError:
        # 处理 EOF（例如管道输入结束）
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
