
# 环境配置
1. `pip install -r requirements.txt`
2. `python test_env.py`
若无报错，则ok
# 脚本功能解释
`resort_folders.py`用于给文件夹重新排序，得到连续序号。
`unzip.py`用于解压刚从mdoelscope上下载下来的数据集，得到raw数据集。
`check.bash`用于检查raw数据集是否有脏东西
`clean_instructions.py`用于把raw数据集里面的instruction.txt里面的语句 最前面的“轨迹n：”那段给删掉
`re_recognize.py`是用于把长程任务中的每个子任务分开，把每个子任务分成长程任务的
`check_instruction_format.py`用于检查instcution.txt里面的格式
`zip.bash`是用来压缩raw数据集后传到modelscope的

上述都是用于操作raw数据的，没问题后即可开始生成lerobot数据集：
`all.bash`是一键运行脚本，需要改一下`SRC_ROOT`和`FINAL_ROOT`。
SRC即为原来的raw文件，FINAL_ROOT即为lerobot数据集存放的位置。



`read.py`用于读取.parquet文件的数据，并保存为csv
注意，如果`data_process/1Parquet-csv2par.py`开了下采样，lerobot数据集里的info.json的fps需要手动改。下采样几倍 即为 5/几倍。比如下采样2倍，则fps改成2.5。