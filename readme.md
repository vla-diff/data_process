
# 环境配置
1. `pip install -r requirements.txt`
2. `python test_env.py`
若无报错，则ok
# 脚本功能解释
## raw数据处理
`resort_folders.py`用于给文件夹重新排序，得到连续序号。
`unzip.py`用于解压刚从mdoelscope上下载下来的数据集，得到raw数据集。
`check.bash`用于检查raw数据集是否有脏东西
`clean_instructions.py`用于把raw数据集里面的instruction.txt里面的语句 最前面的“轨迹n：”那段给删掉
`re_recognize.py`是用于把长程任务中的每个子任务分开，把每个子任务分成长程任务的
`check_instruction_format.py`用于检查instcution.txt里面的格式
`zip.bash`是用来压缩raw数据集后传到modelscope的
`sync_bbox_from_json.py`是把`end_data_split/visual_grounding_label_doubao.py`生成的data.json里面的bbox添加到.csv里的
`split_train_val_ori_data.py`用于分训练集和测试集。
`00Change2OurFormat.py`是好久之前的脚本了。当时应该是用来根据instruction的逗号划分子任务的。


## lerobot数据生成
上述都是用于操作raw数据的，没问题后即可开始生成lerobot数据集：
`all.bash`是一键运行脚本，需要改一下`SRC_ROOT`和`FINAL_ROOT`。
SRC即为原来的raw文件，FINAL_ROOT即为lerobot数据集存放的位置。



`read.py`用于读取.parquet文件的数据，并保存为csv
注意，如果`data_process/1Parquet-csv2par.py`开了下采样，lerobot数据集里的info.json的fps需要手动改。下采样几倍 即为 5/几倍。比如下采样2倍，则fps改成2.5。

## 末尾、非末尾数据划分
end_data_split里的脚本。

`detect_stop_frames.py`是划分的，而`trim_videos_from_stop.py`多了个可视化视频的生成，用于判断划分的对不对。

`split_csv.py`跟`detect_stop_frames`一样，只不过作用对象不是lerobot格式的.parquet了，而是raw数据的.csv文件。他会在data.csv相同一级目录下，生成一个data.json，“非末尾数据”的Answer被固定为"<pred_action>"

`visual_grounding_label_doubao.py`是调用API标注bbox的脚本，读取上面生成的data.json，找到Answer不是"<pred_action>"的index，然后标注对应的图片的bbox。如果成功标注了会把bbox放到data.json中，如果没识别到则对应的Answer是空的。

`draw_bboxes.py`是读取`visual_grounding_label_doubao.py`生成的data.json,并把bbox画出来。

`find_action_answer.py`是用来看data.json标注的咋样的，有没有认为是末尾数据但没标上的。

`test_wrong_json.py`是用来看data.json中，有没有一个像样的bbox都没标出来的，其次是看有没有最后一个step的bbox没标出来的。
`fix_last_step_label.py`如果`test_wrong_json.py`有最后一个step的bbox没标出来的，则这个脚本会把最近的有bbox的index的answer赋值给最后一个step。