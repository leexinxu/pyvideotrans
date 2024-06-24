# %%
from videotrans.task.trans_create import TransCreate
from videotrans.configure import config
import os
from videotrans.util import tools
from tqdm import tqdm
from videotrans.util.tools import send_notification, set_process, set_proxy, get_edge_rolelist, get_elevenlabs_role
import traceback
import sys
from videotrans.translator import run as run_trans
import time
import shutil
import fnmatch
from datetime import datetime
import re

# %%
def log(message):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{current_time} - {message}")

# %%
def get_subtitles(sub_path_zh, sub_path_en):
  subtitles = ''
  if sub_path_zh and os.path.exists(sub_path_zh):
    with open(sub_path_zh, 'r', encoding='utf-8') as f:
        subtitles = f.read()
  elif sub_path_en and os.path.exists(sub_path_en):
    with open(sub_path_en, 'r', encoding='utf-8') as f:
        subtitles = f.read()
  return subtitles

# %%
def translate_to_chinese(text):
    translated_text = ''
    # 使用ChatGpt翻译
    try:
        translated_text = run_trans(
            translate_type='chatGPT',
            text_list=text,
            target_language_name='zh-cn',
            set_p=True,
            inst=None,
            source_code='en')
        print(f"Translation chatGPT: {translated_text=}")
    except Exception as e:
        print(f"Error during translation chatGPT: {e}")
    
    if translated_text:
        return translated_text

    # 使用Google翻译
    try:
        if not config.proxy:
            set_proxy('127.0.0.1:7890')
            print(f"Set proxy: {config.proxy}")

        translated_text = run_trans(
            translate_type='Google',
            text_list=text,
            target_language_name='zh-cn',
            set_p=True,
            inst=None,
            source_code='en')
        print(f"Translation Google: {translated_text=}")
    except Exception as e:
        print(f"Error during translation Google: {e}")
    
    if translated_text:
        return translated_text

    return text

# %%
# 重命名为【中配】中文标题【原标题】.mp4
def rename(output, noextname, ext):
    file_path = os.path.join(output, noextname + "." + ext)
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist")
        return "File does not exist"
    
    # 翻译 noextname 为中文(去掉.视频id)
    translated_name = translate_to_chinese(noextname[:noextname.rfind('.')])

    # 新名称
    new_file_name = f"【中配】{translated_name}【{noextname}】.{ext}"
    
    # 构造新的文件名
    new_file_path = os.path.join(output, new_file_name)

    # 重命名文件
    os.rename(file_path, new_file_path)

    print(f"File {file_path=} renamed to {new_file_path=}")
    return f"File renamed to {new_file_path}"

# %%
def move_files(src_path, dst_dir):
    try:
        # 创建目标目录（如果不存在）
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        
        # 移动主文件
        shutil.move(src_path, os.path.join(dst_dir, os.path.basename(src_path)))
        log(f"Moved: {src_path} to {dst_dir}")
    except Exception as e:
        log(f"Error moving file {src_path}: {e}")

def move_related_files(src_dir, mp4_filename, dst_dir):
    # 通过文件名模糊匹配移动相关文件
    base_name = re.escape(os.path.splitext(mp4_filename)[0])
    pattern = re.compile(rf"{base_name}.*")

    for related_file in os.listdir(src_dir):
        if pattern.match(related_file):
            src_file_path = os.path.join(src_dir, related_file)
            move_files(src_file_path, dst_dir)

# %%
def remove_special_characters_from_file_names(file_path):
    # 创建一个正则表达式模式，匹配除了中文、英文、数字、下划线、连字符、句点之外的特殊字符和空格
    pattern = re.compile(r'[^\u4e00-\u9fa5\w\d\-_.]')

    # 获取文件的目录和文件名
    directory, filename = os.path.split(file_path)

    # 检查文件是否存在
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return file_path

    # 替换文件名中的特殊字符和空格为中划线
    new_filename = pattern.sub('-', filename)

    # 如果新文件名与旧文件名相同，则不重命名
    if new_filename == filename:
        print(f"No special characters to replace in: {file_path}")
        return file_path

    # 获取新文件的完整路径
    new_file_path = os.path.join(directory, new_filename)

    # 重命名文件
    os.rename(file_path, new_file_path)
    print(f"Renamed: {file_path} -> {new_file_path}")
    return new_file_path

# %%
# 输出目录
OUTPUT_DIR = '/Volumes/Data/VideoTranslation/TranslationCompleted'

# 字幕标识和后缀
SRT_EN = ".en.srt"
SRT_CN = ".zh-Hans.srt"

# %%
# 静态参数
config.params['target_dir'] = OUTPUT_DIR
config.params['only_video'] = False
config.params['translate_type'] = 'chatGPT'
config.params['chatgpt_api'] = 'http://127.0.0.1:11434'
config.params['chatgpt_key'] = 'ollama'
config.params['chatgpt_model'] = 'qwen2'
config.params['tts_type'] = 'ChatTTS'
config.params['chattts_api'] = 'http://127.0.0.1:9966'
config.params['voice_role'] = 'seed_2222_restored_emb.pt'
config.params['model_type'] = 'faster'
config.params['whisper_model'] = 'distil-whisper-large-v3'
config.params['whisper_type'] = 'all'
config.params['voice_rate'] = '+0%'
config.params['append_video'] = False
config.params['voice_autorate'] = True
config.params['video_autorate'] = False
config.params['auto_ajust'] = True
config.params['back_audio']='-'
config.params['app_mode'] = 'cli'
config.params['is_batch'] = False
config.params['volume'] = '+0.5%'
config.params['pitch'] = '+0%'
config.params['is_separate'] = True

# %%
# 翻译视频
def translatevideo(source_mp4_path):
    log(f"Translating video: {source_mp4_path}")

    config.params['is_separate'] = True

    # 修改动态参数
    sub_path_en = os.path.splitext(source_mp4_path)[0] + SRT_EN
    sub_path_en = sub_path_en if os.path.exists(sub_path_en) else None

    sub_path_zh = os.path.splitext(source_mp4_path)[0] + SRT_CN
    sub_path_zh = sub_path_zh if os.path.exists(sub_path_zh) else None

    config.params['source_mp4'] = source_mp4_path
    config.params['source_language'] = 'zh-cn' if sub_path_zh else 'en'
    config.params['subtitle_type'] = 1 if sub_path_zh else 3  # 如果存在中文字幕文件，就嵌入硬字幕单中文（此种情况没有英文字幕），否则嵌入硬字幕双语言（中英）
    config.params['subtitles'] = get_subtitles(sub_path_zh, sub_path_en)
    obj_format = tools.format_video(config.params['source_mp4'].replace('\\', '/'), config.params['target_dir'])

    # 开始按钮状态
    config.current_status = 'ing'

    config.settings['countdown_sec'] = 0

    #os.makedirs(os.path.join(os.getcwd(), 'tmp'), exist_ok=True)

    process_bar_data = [
        config.transobj['kaishichuli'],
        config.transobj['kaishishibie'],
        config.transobj['starttrans'],
        config.transobj['kaishipeiyin'],
        config.transobj['kaishihebing'],
    ]

    process_bar = tqdm(process_bar_data)
    try:
        video_task = TransCreate(config.params, obj_format)
        try:
            process_bar.set_description(process_bar_data[0])
            video_task.prepare()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["yuchulichucuo"]}:' + str(e)
            print(err)
            raise
        try:
            process_bar.set_description(process_bar_data[1])
            video_task.recogn()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["shibiechucuo"]}:' + str(e)
            print(err)
            raise
            
        try:
            process_bar.set_description(process_bar_data[2])
            video_task.trans()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["fanyichucuo"]}:' + str(e)
            print(err)
            raise
        try:
            process_bar.set_description(process_bar_data[3])
            video_task.dubbing()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["peiyinchucuo"]}:' + str(e)
            print(err)
            raise
        try:
            process_bar.set_description(process_bar_data[4])
            video_task.hebing()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["hebingchucuo"]}:' + str(e)
            print(err)
            raise
        try:
            video_task.move_at_end()
            process_bar.update(1)
        except Exception as e:
            err=f'{config.transobj["hebingchucuo"]}:' + str(e)
            print(err)
            raise

        send_notification(config.transobj["zhixingwc"], f'"subtitles -> audio"')
        print(f'{"执行完成" if config.defaulelang == "zh" else "Succeed"} {video_task.targetdir_mp4}')

        # 重命名为【中配】中文标题【原标题】.mp4
        rename(obj_format["output"], obj_format["noextname"], obj_format["ext"])

    except Exception as e:
        send_notification(e, f'{video_task.obj["raw_basename"]}')
        # 捕获异常并重新绑定回溯信息
        traceback.print_exc()
        raise

# %%
# 每分钟检查一下是否有新的视频，如果有，则翻译。翻译完移动到翻译完目录
def check_and_translate_videos(src_dir, dst_dir, error_dir):
    log("******* Start Auto Video Trans *******")
    while True:
        log("Checking for new videos...")
        # 获取目录中的所有文件
        files = os.listdir(src_dir)
        mp4_files = [f for f in files if f.endswith('.mp4')]
        log(f"Get new videos : {len(mp4_files)}")
        for mp4_file in mp4_files:
            source_mp4_path = os.path.join(src_dir, mp4_file)

            try:
                # 去除文件名特殊字符
                new_source_mp4_path = remove_special_characters_from_file_names(source_mp4_path)
                if new_source_mp4_path != source_mp4_path:
                    # 重命名字幕文件
                    remove_special_characters_from_file_names(os.path.splitext(source_mp4_path)[0] + SRT_EN)
                    remove_special_characters_from_file_names(os.path.splitext(source_mp4_path)[0] + SRT_CN)

                    source_mp4_path = new_source_mp4_path
                    mp4_file = os.path.basename(source_mp4_path)

                # 翻译视频
                translatevideo(source_mp4_path)
                
                # 移动 .mp4 文件及其相应的字幕文件
                move_files(source_mp4_path, dst_dir)
                move_related_files(src_dir, mp4_file, dst_dir)
            except Exception as e:
                log(f"Error translating video {source_mp4_path}: {e}")
                # 移动 .mp4 文件及其相应的字幕文件到翻译失败目录
                move_related_files(src_dir, mp4_file, error_dir)
                # 删除输出目录
                shutil.rmtree(f'{OUTPUT_DIR}/{os.path.splitext(mp4_file)[0]}')

        # 等待 60 秒再检查
        log("Waiting for 60 seconds before next check...")
        time.sleep(60)

# %%
# 启动自动视频翻译系统
source_directory = '/Volumes/Data/VideoTranslation/YouTubeDownload'
destination_directory = '/Volumes/Data/VideoTranslation/YouTubeDownloadAfterTranslationMove'
error_dir = '/Volumes/Data/VideoTranslation/YouTubeDownloadTranslationError'

check_and_translate_videos(source_directory, destination_directory, error_dir)

# %% [markdown]
# 


