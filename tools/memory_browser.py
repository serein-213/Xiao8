import sqlite3
import os
import pandas as pd

# 定义数据库路径
db_path = './memory/store/time_indexed_test'

try:
    # 连接到SQLite数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询所有表单
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # 打印表单名称和序号
    if tables:
        print("⭐️数据库中的表单:")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table[0]}")

        # 获取用户输入
        while True:
            try:
                choice = int(input("\n⭐️请输入要浏览的表单序号: "))
                if 1 <= choice <= len(tables):
                    selected_table = tables[choice - 1][0]
                    break
                else:
                    print(f"请输入1到{len(tables)}之间的数字")
            except ValueError:
                print("请输入有效的数字")

        # 查询选定表单的结构
        cursor.execute(f"PRAGMA table_info({selected_table})")
        columns_info = cursor.fetchall()
        print(f"\n表 '{selected_table}' 的结构:")
        for col in columns_info:
            print(f"列名: {col[1]}, 类型: {col[2]}")

        # 查询表单数据
        cursor.execute(f"SELECT * FROM {selected_table} LIMIT 10")
        rows = cursor.fetchall()

        # 获取列名
        column_names = [col[1] for col in columns_info]

        # 使用pandas展示数据
        if rows:
            print(f"\n⭐️表 '{selected_table}' 的前10行数据:")
            df = pd.DataFrame(rows, columns=column_names)
            print(df)

            # 提供更多浏览选项
            print("\n⭐️浏览选项:")
            print("1. 查看更多行")
            print("2. 执行自定义SQL查询")
            print("3. 导出数据到CSV")
            print("4. 查询特定时间")
            print("5. 退出")

            option = int(input("请选择操作: "))

            if option == 1:
                num_rows = int(input("⭐️请输入要查看的行数: "))
                cursor.execute(f"SELECT * FROM {selected_table} LIMIT {num_rows}")
                more_rows = cursor.fetchall()
                df = pd.DataFrame(more_rows, columns=column_names)
                print(df)

            elif option == 2:
                custom_query = input(f"⭐️请输入针对表 '{selected_table}' 的SQL查询: ")
                cursor.execute(custom_query)
                query_results = cursor.fetchall()
                # 获取查询结果的列名
                col_names = [description[0] for description in cursor.description]
                df = pd.DataFrame(query_results, columns=col_names)
                print(df)

            elif option == 3:
                export_path = input("⭐️请输入导出CSV的路径(默认为当前目录): ") or f"{selected_table}.csv"
                cursor.execute(f"SELECT * FROM {selected_table}")
                all_rows = cursor.fetchall()
                df = pd.DataFrame(all_rows, columns=column_names)
                df.to_csv(export_path, index=False)
                print(f"⭐️数据已导出到 {export_path}")

            elif option == 4:
                print("\n⭐️请输入时间范围 (格式: YYYY-MM-DD HH:MM)")
                start_datetime = input("开始时间: ")
                end_datetime = input("结束时间: ")

                try:
                    # 验证日期时间格式
                    from datetime import datetime

                    try:
                        # 尝试解析用户输入的日期时间
                        datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
                        datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
                    except ValueError:
                        print("💥日期时间格式错误！请使用格式: YYYY-MM-DD HH:MM (例如: 2025-05-06 14:30)")
                        raise ValueError("日期时间格式错误")

                    # 构建查询
                    query = f"SELECT * FROM {selected_table} WHERE timestamp BETWEEN '{start_datetime}' AND '{end_datetime}'"
                    cursor.execute(query)
                    date_range_rows = cursor.fetchall()

                    if date_range_rows:
                        df = pd.DataFrame(date_range_rows, columns=column_names)
                        print(f"\n⭐️表 '{selected_table}' 在 {start_datetime} 到 {end_datetime} 之间的数据:")
                        print(df)

                        # 提供导出选项
                        export_option = input("\n⭐️是否要导出这些数据到CSV文件? (y/n): ")
                        if export_option.lower() == 'y':
                            export_path = input(
                                "⭐️请输入导出CSV的路径(默认为当前目录的time_range_data.csv): ") or "time_range_data.csv"
                            df.to_csv(export_path, index=False)
                            print(f"⭐️数据已导出到 {export_path}")
                        print(f"⭐️请使用df变量继续浏览DataFrame")
                        import ipdb, json
                        ipdb.set_trace()
                    else:
                        print(f"💥在 {start_datetime} 到 {end_datetime} 之间没有数据")
                except Exception as e:
                    print(f"💥查询出错: {e}")

        else:
            print(f"⭐️表 '{selected_table}' 中没有数据")
    else:
        print("💥数据库中没有表单")

except sqlite3.Error as e:
    print(f"💥SQLite错误: {e}")
finally:
    # 关闭连接
    if 'conn' in locals():
        conn.close()
