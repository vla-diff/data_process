#!/bin/bash




#检查有没有缺少.csv文件的目录
# 检查是否指定了搜索目录（未指定则默认当前目录）
if [ $# -eq 0 ]; then
    SEARCH_DIR=$(pwd)
else
    SEARCH_DIR="$1"
    # 验证目录是否存在
    if [ ! -d "$SEARCH_DIR" ]; then
        echo -e "\033[31m错误：目录 $SEARCH_DIR 不存在！\033[0m"
        exit 1
    fi
fi

echo -e "\033[32m=== 开始搜索目录：$SEARCH_DIR ===\033[0m"
echo -e "正在查找名称为n-m格式且没有data.csv的文件夹（递归遍历）...\n"

count=0

# 递归查找所有符合n-m格式的文件夹，检查是否包含data.csv
# -type d：只找文件夹；-not -path "*/\.*"：排除隐藏文件夹
# -name "[0-9]*-[0-9]*"：匹配n-m格式的文件夹名称
find "$SEARCH_DIR" -type d -not -path "*/\.*" -name "[0-9]*-[0-9]*" | while read -r dir; do
    if [ ! -f "$dir/data.csv" ]; then
        # 红色输出缺失文件的文件夹路径
        echo -e "\033[31m❌ 缺失 data.csv：$dir\033[0m"
        count=$((count + 1))
    fi
done

echo -e "\n\033[32m=== 搜索完成！ ===\033[0m"

# 可选：将结果保存到日志（取消注释下方代码即可）
# LOG_FILE="Special_Folders_No_DataCsv_List_$(date +%Y%m%d_%H%M%S).txt"
# echo "搜索目录：$SEARCH_DIR" > "$LOG_FILE"
# echo "搜索时间：$(date)" >> "$LOG_FILE"
# echo "名称格式为n-m且缺失data.csv的文件夹列表：" >> "$LOG_FILE"
# find "$SEARCH_DIR" -type d -not -path "*/\.*" -name "[0-9]*-[0-9]*" | while read -r dir; do
#     if [ ! -f "$dir/data.csv" ]; then
#         echo "$dir" >> "$LOG_FILE"
#     fi
# done
# echo -e "\033[32m日志已保存到：$LOG_FILE\033[0m"












#检查有没有空的.csv文件
# 检查是否提供了目录参数，未提供则使用当前目录
if [ $# -eq 0 ]; then
    SEARCH_DIR=$(pwd)
else
    SEARCH_DIR="$1"
    # 验证目录是否存在
    if [ ! -d "$SEARCH_DIR" ]; then
        echo -e "\033[31m错误：目录 $SEARCH_DIR 不存在！\033[0m"
        exit 1
    fi
fi

echo -e "\033[32m=== 开始搜索目录：$SEARCH_DIR ===\033[0m"
echo -e "正在查找所有空的CSV文件（递归遍历）...\n"

count=0

# 递归查找所有.csv文件，并检查是否为空
# -type f：只查找文件
# -name "*.csv"：只匹配CSV文件
# -empty：只匹配空文件
find "$SEARCH_DIR" -type f -name "*.csv" -empty | while read -r file; do
    # 红色输出空CSV文件路径
    echo -e "\033[31m❌ 空CSV文件：$file\033[0m"
    count=$((count + 1))
done

echo -e "\n\033[32m=== 搜索完成！ ===\033[0m"