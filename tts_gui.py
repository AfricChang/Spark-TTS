import sys
import os
import csv
import tempfile
import subprocess
import datetime
import torch
import re
import shutil
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QTextEdit, QScrollArea, QGridLayout,
                            QTabWidget, QFrame, QStackedWidget, QComboBox, QPlainTextEdit,
                            QFileDialog,QMenuBar,QDialog, QSplitter)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QEvent, QUrl
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QTextCursor, QCursor
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from qfluentwidgets import (PushButton, TabBar, SearchLineEdit, Slider, 
                           ToggleButton, CardWidget, ToolButton, InfoBar,
                           FluentIcon, ComboBox,Dialog,MessageBox)
import sip

# 资源路径处理
def get_resource_path(relative_path):
    """
    获取资源绝对路径，兼容开发环境和PyInstaller打包后的环境
    """
    
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境下的当前目录
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    full_path = os.path.join(base_path, relative_path)
    
    # 检查文件是否存在并记录
    exists = os.path.exists(full_path)
    
    # 如果文件不存在，尝试在可执行文件目录查找
    if not exists and hasattr(sys, '_MEIPASS'):
        # 获取可执行文件所在目录
        exe_dir = os.path.dirname(sys.executable)
        alternative_path = os.path.join(exe_dir, relative_path)
        alt_exists = os.path.exists(alternative_path)
        
        if alt_exists:
            return alternative_path
    
    return full_path

# 异常处理钩子，用于记录崩溃信息
def excepthook(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常并写入日志文件"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # 在用户桌面创建日志文件
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    log_file = os.path.join(desktop, 'tts_error_log.txt')
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(error_msg)
    
    print(f"错误信息已保存到: {log_file}")

# 设置全局异常处理
import traceback
sys.excepthook = excepthook

# 导入audio_generator模块
# import audio_generator # <-- Remove this

# Import SparkTTS
from cli.SparkTTS import SparkTTS
import soundfile as sf

# 音色信息类
class VoiceInfo:
    def __init__(self, voice_id, name, scene, voice_type, language, sample_rate, emotion):
        self.voice_id = voice_id
        self.name = name
        self.scene = scene
        self.voice_type = voice_type
        self.language = language
        self.sample_rate = sample_rate
        self.emotion = emotion
        # 判断性别
        self.gender = "女声" if ("女声" in scene or not ("男声" in scene)) else "男声"
        self.is_female = self.gender == "女声"

# 修改VoiceCard类，支持暂停功能和显示不同图标
class VoiceCard(CardWidget):
    def __init__(self, voice_info, parent=None):
        super().__init__(parent)
        self.voice_info = voice_info
        self.setFixedSize(180, 80)
        self.is_playing = False  # 添加播放状态跟踪
        
        # 设置鼠标跟踪，以便接收鼠标悬停事件
        self.setMouseTracking(True)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 头像容器，用于放置头像和播放按钮
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(40, 40)
        self.avatar_container_layout = QVBoxLayout(self.avatar_container)
        self.avatar_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 头像
        self.avatar_label = QLabel()
        
        # 根据性别选择头像
        if voice_info.is_female:
            avatar_path = get_resource_path(os.path.join("Resources", "icon-women.svg"))
        else:
            avatar_path = get_resource_path(os.path.join("Resources", "icon-man.svg"))
            
        if os.path.exists(avatar_path):
            # 加载SVG文件
            renderer = QSvgRenderer(avatar_path)
            pixmap = QPixmap(40, 40)
            pixmap.fill(Qt.transparent)  # 确保背景透明
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
        else:
            # 默认头像
            pixmap = QPixmap(40, 40)
            if voice_info.is_female:
                pixmap.fill(Qt.red)  # 默认红色头像-女声
            else:
                pixmap.fill(Qt.blue)  # 默认蓝色头像-男声
        
        self.avatar_label.setPixmap(pixmap)
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_container_layout.addWidget(self.avatar_label)
        
        # 创建播放按钮（初始隐藏）
        self.play_button = ToolButton(self.avatar_container)
        
        # 保存播放和暂停图标路径
        self.play_icon_path = get_resource_path(os.path.join("Resources", "image_icon_listen_play.svg"))
        self.pause_icon_path = get_resource_path(os.path.join("Resources", "image_icon_listen_pause.svg"))
        
        # 设置初始图标为播放
        self.update_play_button_icon()
        
        self.play_button.setFixedSize(30, 30)
        self.play_button.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); border-radius: 15px;")
        self.play_button.setCursor(QCursor(Qt.PointingHandCursor))  # 设置鼠标悬停样式为手型
        self.play_button.clicked.connect(self.play_audio_sample)
        
        # 设置播放按钮在头像中央
        self.play_button.setGeometry(5, 5, 30, 30)  # 居中放置
        self.play_button.hide()  # 初始时隐藏
        
        # 文本信息
        self.info_layout = QVBoxLayout()
        self.name_label = QLabel(voice_info.name)
        self.name_label.setStyleSheet("font-weight: bold;")
        self.description_label = QLabel(voice_info.scene)
        self.description_label.setStyleSheet("color: gray;")
        
        self.info_layout.addWidget(self.name_label)
        self.info_layout.addWidget(self.description_label)
        
        self.layout.addWidget(self.avatar_container)
        self.layout.addLayout(self.info_layout)
        
        # 热门标签 (大模型音色和精品音色添加热门标签)
        if "大模型音色" in voice_info.voice_type or "精品音色" in voice_info.voice_type:
            self.hot_button = PushButton("热门")
            self.hot_button.setFixedSize(40, 20)
            self.hot_button.setStyleSheet("background-color: orange; color: white; border-radius: 5px;")
            self.layout.addWidget(self.hot_button, 0, Qt.AlignTop | Qt.AlignRight)
    
    def update_play_button_icon(self):
        """根据播放状态更新按钮图标"""
        if self.is_playing:
            # 正在播放，显示暂停图标
            if os.path.exists(self.pause_icon_path):
                pause_renderer = QSvgRenderer(self.pause_icon_path)
                pause_pixmap = QPixmap(30, 30)
                pause_pixmap.fill(Qt.transparent)
                pause_painter = QPainter(pause_pixmap)
                pause_renderer.render(pause_painter)
                pause_painter.end()
                self.play_button.setIcon(QIcon(pause_pixmap))
            else:
                # 如果找不到SVG，使用内置图标
                self.play_button.setIcon(FluentIcon.PAUSE)
        else:
            # 未播放，显示播放图标
            if os.path.exists(self.play_icon_path):
                play_renderer = QSvgRenderer(self.play_icon_path)
                play_pixmap = QPixmap(30, 30)
                play_pixmap.fill(Qt.transparent)
                play_painter = QPainter(play_pixmap)
                play_renderer.render(play_painter)
                play_painter.end()
                self.play_button.setIcon(QIcon(play_pixmap))
            else:
                # 如果找不到SVG，使用内置图标
                self.play_button.setIcon(FluentIcon.PLAY)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.play_button.show()
        # 如果正在播放，确保显示暂停图标
        if self.is_playing:
            self.update_play_button_icon()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.play_button.hide()
        super().leaveEvent(event)
    
    def set_playing_state(self, is_playing):
        """设置播放状态"""
        self.is_playing = is_playing
        self.update_play_button_icon()
    
    def play_audio_sample(self):
        """播放或暂停音色示例"""
        # 通过找到父窗口来调用播放函数
        app = self.window()
        if app and hasattr(app, 'find_audio_sample') and hasattr(app, 'play_sample_audio'):
            voice_id = self.voice_info.voice_id
            
            if self.is_playing:
                # 如果正在播放，则暂停
                app.pause_sample_audio(self)
                # 添加日志
                if hasattr(app, 'log'):
                    app.log(f"暂停音色 {self.voice_info.name} (ID: {voice_id}) 的示例音频")
            else:
                # 如果未播放，则播放
                audio_file = app.find_audio_sample(voice_id)
                if audio_file:
                    app.play_sample_audio(self, audio_file)
                    # 添加日志
                    if hasattr(app, 'log'):
                        app.log(f"播放音色 {self.voice_info.name} (ID: {voice_id}) 的示例音频")
                else:
                    # 未找到音频文件时通知用户
                    if hasattr(app, 'log'):
                        app.log(f"未找到音色 {self.voice_info.name} 的示例音频")
                    
                    InfoBar.warning(
                        title="警告",
                        content=f"未找到音色 {self.voice_info.name} 的示例音频",
                        parent=app
                    )
        
    def mousePressEvent(self, event):
        # 选中效果
        self.setStyleSheet("background-color: #e0e0e0; border: 2px solid #1890ff; border-radius: 5px;")
        super().mousePressEvent(event)

# 日志输出重定向类
class LogRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        
    def write(self, text):
        self.buffer += text
        if text.endswith('\n'):
            self.text_widget.appendPlainText(self.buffer.rstrip())
            self.buffer = ""
            # 自动滚动到底部
            self.text_widget.moveCursor(QTextCursor.End)
    
    def flush(self):
        if self.buffer:
            self.text_widget.appendPlainText(self.buffer)
            self.buffer = ""

# 创建一个线程类来运行语音合成任务
class SynthesisThread(QThread):
    synthesis_complete = pyqtSignal(bool, str)  # 信号：合成完成(成功/失败, 输出文件路径)
    progress_update = pyqtSignal(str)  # 信号：进度更新

    def __init__(self, text, prompt_text, prompt_speech_path, output_path, model_dir, device):
        super().__init__()
        self.text = text
        self.prompt_text = prompt_text
        self.prompt_speech_path = prompt_speech_path
        self.output_path = output_path
        self.model_dir = model_dir  # 恢复模型目录参数 
        self.device = device        # 恢复设备参数
        # 不再接收预加载的模型

    def run(self):
        # Redirect stdout to capture progress
        original_stdout = sys.stdout
        sys.stdout = self
        
        success = False
        start_time = time.time() # Record start time
        synthesis_duration = 0
        
        # 记录更详细的输入信息
        self.progress_update.emit("---合成任务开始---")
        self.progress_update.emit(f"文本长度: {len(self.text)} 字符")
        self.progress_update.emit(f"参考文本长度: {len(self.prompt_text)} 字符")
        self.progress_update.emit(f"参考音频路径: {self.prompt_speech_path}")
        self.progress_update.emit(f"输出路径: {self.output_path}")
        
        try:
            # 每次创建新的模型实例
            self.progress_update.emit(f"正在加载 Spark-TTS 模型 (目录: {self.model_dir}, 设备: {self.device})...")
            model_load_start = time.time()
            tts_model = SparkTTS(model_dir=self.model_dir, device=self.device)
            model_load_end = time.time()
            model_load_duration = model_load_end - model_load_start
            self.progress_update.emit(f"模型加载完成，耗时 {model_load_duration:.2f} 秒")
            
            # 输出更多诊断信息
            text_length = len(self.text) if self.text else 0
            self.progress_update.emit(f"准备合成文本: 【{self.text[:100]}...】")
            if text_length < 30:
                self.progress_update.emit(f"警告: 文本长度较短 ({text_length} 字符)，可能会导致合成失败")
            
            self.progress_update.emit("开始合成...")
            
            # 特别处理可能会导致语义令牌问题的情况
            if self.text.startswith("每日资讯") or re.search(r'^\d+[、.．]', self.text):
                self.progress_update.emit("检测到可能导致问题的文本格式（标题或编号）")
                # 尝试移除可能导致问题的格式
                cleaned_text = re.sub(r'^(每日资讯.*?\n|^\d+[、.．])', '', self.text)
                self.progress_update.emit(f"已尝试清理文本格式，处理前: {len(self.text)} 字符，处理后: {len(cleaned_text)} 字符")
                self.text = cleaned_text
                
            inference_start_time = time.time() # Start timing inference
            # 使用新创建的模型实例
            try:
                self.progress_update.emit(f"开始推理...参考音频: {os.path.basename(self.prompt_speech_path)}")
                wav = tts_model.inference(
                    text=self.text,
                    prompt_text=self.prompt_text,
                    prompt_speech_path=self.prompt_speech_path
                )
                inference_end_time = time.time() # End timing inference
                synthesis_duration = inference_end_time - inference_start_time
                
                if wav is not None:
                    write_start_time = time.time()
                    sf.write(self.output_path, wav, 16000)
                    write_end_time = time.time()
                    write_duration = write_end_time - write_start_time
                    success = True
                    # Include duration in the success message
                    self.progress_update.emit(f"合成成功！耗时: {synthesis_duration:.2f} 秒 (写入文件: {write_duration:.2f} 秒)。音频已保存到: {self.output_path}")
                else:
                    self.progress_update.emit("合成失败：模型未能生成有效音频。")
            except ValueError as ve:
                # 特别处理"Semantic tokens are empty"错误
                if "Semantic tokens are empty" in str(ve):
                    error_msg = f"【关键错误】语义令牌为空，这通常由于以下原因导致:\n" 
                    error_msg += f"1. 文本太短或格式不适合合成 (当前长度: {text_length})\n"
                    error_msg += f"2. 参考音频与文本不匹配\n"
                    error_msg += f"3. 文本开头有数字编号、特殊符号等\n"
                    error_msg += f"合成文本内容: '{self.text[:100]}{'...' if len(self.text)>100 else ''}'"
                    self.progress_update.emit(error_msg)
                    
                    # 尝试更强的干预措施 - 修改处理方式，不再截断文本
                    try:
                        # 简化文本，但保留所有内容
                        simple_text = self.text.replace("\n", " ") # 将换行替换为空格
                        simple_text = re.sub(r'\d+[、.．]', '', simple_text) # 移除数字标记
                        simple_text = re.sub(r'[，。？！；,.!?;]', '，', simple_text) # 统一标点为逗号，保持句子结构
                        
                        # 确保文本长度合适，但不截断
                        if len(simple_text) < 30:
                            # 如果太短，重复文本
                            simple_text = simple_text * 2
                            
                        self.progress_update.emit(f"尝试使用简化后的完整文本重新合成 (长度: {len(simple_text)} 字符)")
                        
                        # 再次尝试合成
                        wav = tts_model.inference(
                            text=simple_text,
                            prompt_text=self.prompt_text,
                            prompt_speech_path=self.prompt_speech_path
                        )
                        
                        if wav is not None:
                            sf.write(self.output_path, wav, 16000)
                            success = True
                            self.progress_update.emit(f"使用简化文本合成成功！音频已保存到: {self.output_path}")
                        else:
                            self.progress_update.emit("使用简化文本合成仍然失败。")
                            
                            # 第三次尝试：使用更简单的文本，但保持一定长度
                            self.progress_update.emit("尝试最后的方法：使用更简化的文本...")
                            final_attempt_text = "这是一段测试语音，用于测试语音合成系统。" + simple_text[:100]
                            wav = tts_model.inference(
                                text=final_attempt_text,
                                prompt_text=self.prompt_text,
                                prompt_speech_path=self.prompt_speech_path
                            )
                            
                            if wav is not None:
                                sf.write(self.output_path, wav, 16000)
                                success = True
                                self.progress_update.emit(f"最终尝试合成成功！但音频可能不完整，请检查结果。")
                            else:
                                self.progress_update.emit("所有尝试均失败，无法完成合成。")
                    except Exception as retry_e:
                        self.progress_update.emit(f"重试合成时发生错误: {retry_e}")
                else:
                    # 其他ValueError错误
                    error_msg = f"合成值错误: {ve}\n{traceback.format_exc()}"
                    self.progress_update.emit(error_msg)
            except Exception as e:
                # 处理其他异常
                error_msg = f"合成时发生错误: {e}\n{traceback.format_exc()}"
                self.progress_update.emit(error_msg)

        except Exception as e:
            # Make sure to log the full traceback in case of inference errors
            error_msg = f"合成线程中发生错误: {e}\n{traceback.format_exc()}"
            self.progress_update.emit(error_msg)
            print(error_msg) # Also print to console/log
        finally:
            end_time = time.time() # Record end time for the whole process
            total_duration = end_time - start_time
            self.progress_update.emit(f"线程总耗时: {total_duration:.2f} 秒") # Log total thread time
            self.progress_update.emit("---合成任务结束---")
            sys.stdout = original_stdout # Restore stdout
            self.synthesis_complete.emit(success, self.output_path)

    def write(self, text):
        # 捕获print输出并发送为进度更新
        if text.strip(): # Avoid sending empty lines
            self.progress_update.emit(text.strip())

    def flush(self):
        # 必须有的方法，用于io操作
        pass

# TTSApp类定义
class TTSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.voice_list = []
        self.voice_by_scene = {}
        self.all_scenes = []
        self.all_genders = ["女声", "男声"]
        self.current_scene = None
        self.current_gender = None
        self.current_type = None
        
        # 初始化媒体播放器
        self.media_player = QMediaPlayer()
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        
        # 添加专门用于示例音频的播放器
        self.sample_player = QMediaPlayer()
        self.sample_player.stateChanged.connect(self.sample_state_changed)
        
        # 跟踪当前正在播放示例音频的音色卡片
        self.current_playing_card = None
        
        # Store SparkTTS specific parameters
        self.model_dir = "pretrained_models/Spark-TTS-0.5B" # Make this configurable later?
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.selected_prompt_audio_path = "" # Path for prompt audio

        # State variables for chunked synthesis
        self.is_chunked_synthesis = False
        self.text_chunks = []
        self.current_chunk_index = 0
        self.temp_audio_files = []
        self.final_output_path = "" # Store the path for the final merged file
        self.ffmpeg_path = None # Store path to ffmpeg executable
        self.tts_model = None # Placeholder for the loaded TTS model instance
        
        # Load voices first as UI might depend on it
        self.voice_list = [] # Initialize voice list
        self.load_voice_types()

        # Setup UI
        self.initUI()

        # Update UI elements after it's built
        self.update_voice_list() # Populate voice grid etc.
        self.log("系统初始化完成")
        self.log(f"检测到设备: {self.device}")

        # Check for ffmpeg at the specified relative path
        relative_ffmpeg_path = os.path.join("softwares", "ffmpeg", "ffmpeg.exe")
        absolute_ffmpeg_path = get_resource_path(relative_ffmpeg_path)

        if os.path.exists(absolute_ffmpeg_path) and os.path.isfile(absolute_ffmpeg_path):
            self.ffmpeg_path = absolute_ffmpeg_path
            self.log(f"检测到 FFmpeg: {self.ffmpeg_path}，长文本合成已启用。")
        else:
            self.log(f"警告：未在预期路径 {relative_ffmpeg_path} 找到 FFmpeg，长文本合并功能将不可用。")
            self.log(f"(尝试查找的绝对路径: {absolute_ffmpeg_path})")

    def load_voice_types(self):
        """从CSV文件加载音色类型"""
        try:
            # 使用get_resource_path获取CSV文件的路径
            csv_path = get_resource_path('config/tencent_cloud_voice_type.csv')
            
            # 默认初始化all_types为空列表，确保即使文件加载失败也有一个有效的属性
            self.all_types = []
            
            # 打印路径信息以便调试
            print(f"尝试加载音色文件: {csv_path}")
            print(f"此路径是否存在: {os.path.exists(csv_path)}")
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过标题行
                
                scenes_set = set()  # 用于收集不重复的场景类型
                types_set = set()   # 用于收集不重复的音色类型
                
                for row in reader:
                    if len(row) >= 7:
                        voice_id = row[0]
                        name = row[1]
                        scene = row[2]
                        voice_type = row[3]
                        language = row[4]
                        sample_rate = row[5]
                        emotion = row[6]
                        
                        voice_info = VoiceInfo(voice_id, name, scene, voice_type, language, sample_rate, emotion)
                        self.voice_list.append(voice_info)
                        
                        # 提取场景，去掉"男声"、"女声"字样
                        cleaned_scene = scene
                        for gender in ["男声", "女声"]:
                            cleaned_scene = cleaned_scene.replace(gender, "")
                        cleaned_scene = cleaned_scene.strip()
                        
                        # 收集唯一场景和类型
                        scenes_set.add(cleaned_scene)
                        types_set.add(voice_type)
                        
                        # 按推荐场景分组
                        if cleaned_scene not in self.voice_by_scene:
                            self.voice_by_scene[cleaned_scene] = []
                            
                        self.voice_by_scene[cleaned_scene].append(voice_info)
                
                # 将场景集合转换为列表并排序
                self.all_scenes = sorted(list(scenes_set))
                self.all_types = sorted(list(types_set))
                        
            print(f"已加载 {len(self.voice_list)} 种音色，{len(self.all_scenes)} 种场景，{len(self.all_types)} 种类型")
            
        except Exception as e:
            error_msg = f"加载音色文件失败: {e}"
            print(error_msg)
            # 确保基本属性被初始化，即使在文件加载失败时
            if not hasattr(self, 'voice_list') or self.voice_list is None:
                self.voice_list = []
            if not hasattr(self, 'all_scenes') or self.all_scenes is None:
                self.all_scenes = []
            if not hasattr(self, 'all_types') or self.all_types is None:
                self.all_types = []
                
            # 如果打包后，将日志写入桌面
            if hasattr(sys, '_MEIPASS'):
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                log_file = os.path.join(desktop, 'tts_error_log.txt')
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"{error_msg}\n")
                    f.write(f"尝试加载的文件路径: {csv_path}\n")
                    if 'csv_path' in locals():
                        f.write(f"此路径是否存在: {os.path.exists(csv_path)}\n")
                    f.write(f"PyInstaller临时目录: {getattr(sys, '_MEIPASS', '未打包')}\n")
                    f.write(f"当前工作目录: {os.getcwd()}\n")
                    f.write(f"程序所在目录: {os.path.dirname(os.path.abspath(__file__))}\n")
    
    def find_audio_sample(self, voice_id):
        """查找音色对应的示例音频"""
        voice_id_str = str(voice_id)
        
        # 使用get_resource_path获取音频目录
        audio_dirs = [
            get_resource_path(os.path.join("AudioResources", "标准音色")),
            get_resource_path(os.path.join("AudioResources", "大模型音色")),
            get_resource_path(os.path.join("AudioResources", "精品音色"))
        ]
        
        for dir_path in audio_dirs:
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.startswith(voice_id_str) and (file.endswith('.mp3') or file.endswith('.wav')):
                        return os.path.join(dir_path, file)
        
        return None

    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = QMenuBar(self)
        menu_bar.setFixedHeight(30)
        
        # 添加"帮助"菜单
        help_menu = menu_bar.addMenu("帮助")
        
        # 添加"关于"菜单项
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about_dialog)
        
        # 将菜单栏添加到主布局
        self.layout().setMenuBar(menu_bar)
    
    def show_about_dialog(self):
        """显示关于对话框"""
        # 创建自定义对话框
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("关于")
        about_dialog.setFixedSize(400, 300)
        
        # 创建对话框布局
        layout = QVBoxLayout(about_dialog)
        
        # 添加标题
        title_label = QLabel("腾讯云语音合成工具")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 添加版本信息
        version_label = QLabel("版本: 1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 添加项目描述
        description = QLabel(
            "本工具基于腾讯云语音合成服务，提供多种音色选择和语音合成功能。\n"
            "支持调节语速、音量，并可保存合成的音频文件。"
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignLeft)
        layout.addWidget(description)
        
        # 添加开源信息（使用HTML格式支持超链接）
        github_link = QLabel(
            '项目开源地址: <a href="https://github.com/AfricChang/TencentCloud_Audio_generator">GitHub</a>'
        )
        github_link.setOpenExternalLinks(True)  # 允许打开外部链接
        github_link.setAlignment(Qt.AlignCenter)
        layout.addWidget(github_link)
        
        # 添加版权信息
        copyright_label = QLabel("© 2025 AfricChang. 保留所有权利。")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 添加确定按钮
        button_layout = QHBoxLayout()
        ok_button = PushButton("确定")
        ok_button.clicked.connect(about_dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 显示对话框
        about_dialog.exec_()
    
    def initUI(self):
        self.setWindowTitle("Spark-TTS 语音合成工具")
        self.setWindowIcon(QIcon(get_resource_path("Resources/logo.ico")))
        self.setGeometry(100, 100, 1000, 750) # Adjust size if needed
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Menu Bar
        self.menu_bar = self.create_menu_bar()
        self.main_layout.setMenuBar(self.menu_bar)

        # Top Layout (Splitter for resizable panels)
        self.top_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.top_splitter, 1) # Add splitter with stretch factor

        # --- Left Panel (Synthesis Inputs) ---
        self.left_panel = QFrame()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(10, 10, 10, 10)

        # Prompt Audio
        self.prompt_audio_label = QLabel("参考音频 (.wav):")
        self.prompt_audio_layout = QHBoxLayout()
        self.prompt_audio_path_edit = SearchLineEdit(self)
        self.prompt_audio_path_edit.setPlaceholderText("选择参考音频文件路径")
        self.prompt_audio_path_edit.setReadOnly(True)
        self.browse_prompt_audio_button = PushButton("浏览")
        self.browse_prompt_audio_button.clicked.connect(self.browse_prompt_audio)
        self.prompt_audio_layout.addWidget(self.prompt_audio_path_edit)
        self.prompt_audio_layout.addWidget(self.browse_prompt_audio_button)
        self.left_layout.addWidget(self.prompt_audio_label)
        self.left_layout.addLayout(self.prompt_audio_layout)

        # Prompt Text
        self.prompt_text_label = QLabel("参考音频文本:")
        self.prompt_text_edit = QLineEdit(self)
        self.prompt_text_edit.setPlaceholderText("输入参考音频对应的文本")
        self.left_layout.addWidget(self.prompt_text_label)
        self.left_layout.addWidget(self.prompt_text_edit)
        
        self.left_layout.addSpacing(15) # Add some space

        # Target Text
        self.text_input_label = QLabel("合成文本:")
        self.text_input = QPlainTextEdit(self)
        self.text_input.setPlaceholderText("在此输入要合成的文本...")
        self.text_input.textChanged.connect(self.check_text_length)
        self.char_count_label = QLabel("字符数: 0/1000")
        self.char_count_label.setAlignment(Qt.AlignRight)
        self.left_layout.addWidget(self.text_input_label)
        self.left_layout.addWidget(self.text_input)
        self.left_layout.addWidget(self.char_count_label)

        # Synthesize button
        self.synthesize_button = PushButton("开始合成")
        self.synthesize_button.setFixedWidth(120)
        self.synthesize_button.setIcon(FluentIcon.PLAY)
        self.synthesize_button.clicked.connect(self.on_synthesize)
        self.left_layout.addSpacing(10)
        self.left_layout.addWidget(self.synthesize_button, 0, Qt.AlignHCenter)
        self.left_layout.addStretch(1) # Add stretch to push button up
        
        self.top_splitter.addWidget(self.left_panel)

        # --- Right Panel (Original UI - Kept for now, consider removing later) ---
        self.right_panel = QFrame()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(10, 10, 10, 10)

        # Search and Filters
        self.filter_layout = QHBoxLayout()
        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("搜索音色名称...")
        self.search_edit.textChanged.connect(self.filter_voices)
        # ... (Add back other filters like scene, gender, type combo boxes if needed)
        # self.scene_combo = ComboBox()
        # ... Add filter widgets back to filter_layout ...
        self.filter_layout.addWidget(self.search_edit)
        self.right_layout.addLayout(self.filter_layout)

        # Voice Grid
        self.voice_scroll_area = QScrollArea()
        self.voice_scroll_area.setWidgetResizable(True)
        self.voice_grid_widget = QWidget()
        self.voice_grid_layout = QGridLayout(self.voice_grid_widget)
        self.voice_scroll_area.setWidget(self.voice_grid_widget)
        self.right_layout.addWidget(self.voice_scroll_area)

        # Speed and Volume Sliders
        self.speed_label = QLabel("语速: 0.0")
        self.speed_slider = Slider(Qt.Horizontal)
        # ... (Configure speed slider range and connection)
        self.volume_label = QLabel("音量: 50")
        self.volume_slider = Slider(Qt.Horizontal)
        # ... (Configure volume slider range and connection)
        # self.right_layout.addWidget(self.speed_label)
        # self.right_layout.addWidget(self.speed_slider)
        # self.right_layout.addWidget(self.volume_label)
        # self.right_layout.addWidget(self.volume_slider)
        # Note: Speed/Volume sliders are commented out as SparkTTS doesn't use them directly

        self.top_splitter.addWidget(self.right_panel)
        self.top_splitter.setSizes([400, 600]) # Initial size distribution

        # --- Bottom Panel (Log & Player) ---
        self.bottom_panel = QFrame()
        self.bottom_panel.setFixedHeight(200) # Fixed height for bottom panel
        self.bottom_layout = QHBoxLayout(self.bottom_panel)
        self.bottom_layout.setContentsMargins(10, 5, 10, 5)

        # Log Area
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumBlockCount(500)
        # Add clear log button?
        self.bottom_layout.addWidget(self.log_area, 2) # Log takes more space

        # Player Area
        self.player_area = QFrame()
        self.player_layout = QVBoxLayout(self.player_area)
        # ... (Add player elements: label, play button, slider)
        self.player_label = QLabel("无音频")
        self.player_controls = QHBoxLayout()
        self.play_button = PushButton(FluentIcon.PLAY, "播放")
        self.play_button.clicked.connect(self.on_play_audio)
        self.play_button.setEnabled(False)
        self.player_slider = Slider(Qt.Horizontal)
        self.player_slider.setEnabled(False)
        # ... (Connect player slider signals)
        self.player_controls.addWidget(self.play_button)
        self.player_controls.addWidget(self.player_slider)
        self.player_layout.addWidget(self.player_label)
        self.player_layout.addLayout(self.player_controls)
        self.bottom_layout.addWidget(self.player_area, 1)

        self.main_layout.addWidget(self.bottom_panel)

        # Redirect stdout to log area
        sys.stdout = LogRedirector(self.log_area)
        # Set style sheet or other final initializations
        # self.setStyleSheet("...")

    def check_text_length(self):
        """检查文本长度，并启用或禁用合成按钮"""
        text = self.text_input.toPlainText()
        has_text = len(text.strip()) > 0
        self.synthesize_button.setEnabled(has_text)
    
    def log(self, message):
        """添加日志到输出框"""
        self.log_area.appendPlainText(message)
        # 自动滚动到底部
        self.log_area.moveCursor(QTextCursor.End)
    
    def clear_log(self):
        """清除日志"""
        self.log_area.clear()
        self.log("日志已清除")
    
    def update_voice_list(self):
        """更新左侧音色列表显示"""
        # 停止正在播放的示例音频
        if self.current_playing_card:
            self.sample_player.stop()
            self.current_playing_card = None
        
        # 清理旧的布局
        if self.voice_grid_widget.layout():
            QWidget().setLayout(self.voice_grid_widget.layout())
        
        left_layout = QVBoxLayout(self.voice_grid_widget)
        
        # 确定显示哪些音色，通过应用所有筛选条件
        voices_to_display = self.voice_list.copy()
        
        # 筛选场景
        if self.current_scene and self.current_scene != "全部场景":
            filtered_voices = []
            for voice in voices_to_display:
                # 清理场景名称进行比较
                cleaned_scene = voice.scene
                for gender in ["男声", "女声"]:
                    cleaned_scene = cleaned_scene.replace(gender, "")
                cleaned_scene = cleaned_scene.strip()
                
                if cleaned_scene == self.current_scene:
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 筛选性别
        if self.current_gender and self.current_gender != "全部性别":
            filtered_voices = []
            for voice in voices_to_display:
                if voice.gender == self.current_gender:
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 筛选类型
        if self.current_type and self.current_type != "全部类型":
            filtered_voices = []
            for voice in voices_to_display:
                if voice.voice_type == self.current_type:
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 搜索过滤
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            filtered_voices = []
            for voice in voices_to_display:
                if (search_text in voice.name.lower() or 
                    search_text in voice.scene.lower()):
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 按推荐场景对音色进行分组显示
        # 整理场景分组
        scene_groups = {}
        
        # 将音色按场景分组
        for voice in voices_to_display:
            cleaned_scene = voice.scene
            for gender in ["男声", "女声"]:
                cleaned_scene = cleaned_scene.replace(gender, "")
            cleaned_scene = cleaned_scene.strip()
            
            if cleaned_scene not in scene_groups:
                scene_groups[cleaned_scene] = []
                
            scene_groups[cleaned_scene].append(voice)
        
        # 添加各场景分组
        for scene, voices in scene_groups.items():
            if voices:  # 如果该分组有音色
                scene_label = QLabel(scene)
                scene_label.setStyleSheet("font-weight: bold; font-size: 14px;")
                left_layout.addWidget(scene_label)
                
                scene_grid = QGridLayout()
                
                for i, voice in enumerate(voices):
                    card = VoiceCard(voice)
                    card.mousePressEvent = lambda event, v=voice: self.on_voice_selected(event, v)
                    scene_grid.addWidget(card, i // 3, i % 3)
                
                left_layout.addLayout(scene_grid)
        
        # 添加伸展因子确保内容可滚动
        left_layout.addStretch(1)
        
        # 如果没有音色显示，添加提示
        if not voices_to_display:
            no_voice_label = QLabel("没有找到匹配的音色")
            no_voice_label.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(no_voice_label)
        
        # 记录筛选结果
        if hasattr(self, 'log_area'):
            self.log(f"显示 {len(voices_to_display)} 种音色")
    
    def on_scene_changed(self, scene_text):
        """处理场景下拉框选择变化"""
        self.current_scene = scene_text
        self.log(f"选择场景: {scene_text}")
        self.update_voice_list()
    
    def on_gender_changed(self, gender_text):
        """处理性别下拉框选择变化"""
        self.current_gender = gender_text
        self.log(f"选择性别: {gender_text}")
        self.update_voice_list()
    
    def on_type_changed(self, type_text):
        """处理类型下拉框选择变化"""
        self.current_type = type_text
        self.log(f"选择类型: {type_text}")
        self.update_voice_list()
    
    def on_voice_selected(self, event, voice_info):
        """处理音色选择"""
        # 如果正在播放示例音频，停止播放
        if self.current_playing_card:
            self.sample_player.stop()
            try:
                if self.current_playing_card.isVisible() and not sip.isdeleted(self.current_playing_card):
                    self.current_playing_card.set_playing_state(False)
            except (RuntimeError, ReferenceError, Exception):
                pass
            self.current_playing_card = None
            
        # 更新选中的音色
        if hasattr(self, 'selected_voice'):
            # 移除旧的选中音色
            self.selected_voice.setParent(None)
        
        # 创建新的音色卡片
        self.selected_voice = VoiceCard(voice_info)
        self.selected_voice.setFixedSize(180, 60)
        
        # 查找右侧面板的选中音色布局
        for i in range(self.voice_grid_layout.count()):
            item = self.voice_grid_layout.itemAt(i)
            if isinstance(item, QGridLayout) and item.indexOf(self.voice_scroll_area) >= 0:
                # 找到分栏布局
                scene_grid = item
                # 找到右侧面板
                right_panel = scene_grid.itemAt(0).widget()
                # 找到右侧面板的布局
                right_layout = right_panel.layout()
                # 找到选中音色布局
                selected_voice_layout = right_layout.itemAt(0).layout()
                
                # 清空现有内容
                while selected_voice_layout.count():
                    item = selected_voice_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # 添加新的选中音色
                selected_voice_layout.addWidget(self.selected_voice)
                selected_voice_layout.addStretch(1)
                break
        
        # 调用原始的点击事件处理
        QWidget.mousePressEvent(self.selected_voice, event)
        
        # 记录选择的音色
        self.log(f"已选择音色: {voice_info.name} (ID: {voice_info.voice_id})")
    
    def update_speed_value(self, value):
        """更新语速值显示"""
        real_value = value / 10.0
        self.speed_label.setText(f"语速: {real_value:.1f}")
    
    def update_volume_value(self, value):
        """更新音量值显示"""
        self.volume_label.setText(f"音量: {value}")
    
    def on_synthesize(self):
        """开始语音合成（支持分块）"""
        text = self.text_input.toPlainText().strip()
        prompt_text = self.prompt_text_edit.text().strip()
        prompt_audio_path = self.selected_prompt_audio_path
        
        # 临时更改：尝试不分块，直接合成
        USE_SIMPLE_MODE = True  # 设置为True来尝试简单模式
        
        # --- Input Validation --- 
        if not text:
            InfoBar.warning("提示", "请输入要合成的文本", parent=self)
            return
        if not prompt_audio_path:
            InfoBar.warning("提示", "请选择参考音频文件 (.wav 或 .mp3)", parent=self)
            return
        if not prompt_text:
            InfoBar.warning("提示", "请输入参考音频对应的文本", parent=self)
            return
        if not os.path.exists(prompt_audio_path) or not prompt_audio_path.lower().endswith(('.wav', '.mp3')):
            InfoBar.error("错误", "参考音频文件无效或不是有效的音频格式", parent=self)
            return
        # -------------------------

        # --- Reset State for Chunked Synthesis ---
        self.is_chunked_synthesis = False
        self.text_chunks = []
        self.current_chunk_index = 0
        self.temp_audio_files = []
        self.final_output_path = ""
        # ----------------------------------------

        self.log(f"准备使用 Spark-TTS 合成文本...")
        self.log(f"参考音频: {prompt_audio_path}")
        self.log(f"参考文本: '{prompt_text}'")
        self.log(f"要合成的文本长度: {len(text)} 字符")
        
        # 检查文本长度是否过长，如果过长，给予特别提示
        if len(text) > 500:
            self.log(f"注意：文本较长 ({len(text)} 字符)，这可能导致合成速度变慢")
            InfoBar.info(
                title="文本较长",
                content="检测到较长文本，合成可能需要更多时间",
                parent=self,
                duration=3000
            )

        # 禁用合成按钮，防止重复点击
        self.synthesize_button.setEnabled(False)
        self.synthesize_button.setText("合成中...")

        # 使用简单模式（不分块）
        if USE_SIMPLE_MODE:
            self.log("使用简单模式（不分块）进行合成...")
            
            # 温和清理文本以提高成功率，但确保保留大部分内容
            cleaned_text = self._clean_text_for_synthesis(text)
            self.log(f"清理后文本长度: {len(cleaned_text)} 字符")
            
            # 准备输出路径
            output_dir = get_resource_path("Resources/output")
            try:
                os.makedirs(output_dir, exist_ok=True)
                now = datetime.datetime.now()
                output_filename = f"sparktts_simple_{now.strftime('%Y%m%d_%H%M%S')}.wav"
                output_path = os.path.join(output_dir, output_filename)
                self.log(f"输出路径: {output_path}")
            except Exception as e:
                self.log(f"创建输出目录或文件名时出错: {e}")
                InfoBar.error("错误", f"无法准备输出路径: {e}", parent=self)
                self.synthesize_button.setEnabled(True)
                self.synthesize_button.setText("开始合成")
                return
            
            # 显示合成信息
            if len(cleaned_text) != len(text):
                self.log(f"注意：清理文本过程中移除了 {len(text) - len(cleaned_text)} 个字符")
            
            # 创建并启动合成线程
            self.synthesis_thread = SynthesisThread(
                text=cleaned_text,
                prompt_text=prompt_text,
                prompt_speech_path=prompt_audio_path,
                output_path=output_path,
                model_dir=self.model_dir,
                device=self.device
            )
            self.synthesis_thread.progress_update.connect(self.log)
            self.synthesis_thread.synthesis_complete.connect(self.on_synthesis_complete_standard)
            self.synthesis_thread.start()
            return
            
    def on_synthesis_complete_standard(self, success, output_path):
        """标准（单次）合成完成后的处理"""
        # Re-enable button
        self.synthesize_button.setEnabled(True)
        self.synthesize_button.setText("开始合成")
        
        if success and os.path.exists(output_path):
            self.log(f"合成成功，音频文件保存在: {output_path}")
            # Update the audio player controls
            self.current_audio_file = output_path  # 保存当前文件路径
            self.play_button.setEnabled(True)
            self.player_slider.setEnabled(True)
            self.player_label.setText(os.path.basename(output_path))
            InfoBar.success("成功", "语音合成完成！", parent=self)
            # 自动播放合成的音频
            self.play_audio_file(output_path)
        else:
            self.log(f"合成失败. Success: {success}, Path: {output_path}")
            # Clear player state
            self.current_audio_file = None
            self.play_button.setEnabled(False)
            self.player_slider.setEnabled(False)
            self.player_slider.setValue(0)
            self.player_label.setText("无音频")
            InfoBar.error("失败", "语音合成失败，请检查日志获取详细信息", parent=self)
            
        # Clean up thread reference
        self.synthesis_thread = None # Allow garbage collection
        
    def _clean_text_for_synthesis(self, text):
        """更温和地清理文本，保留更多原始内容"""
        if not text or len(text.strip()) < 5:
            self.log("警告：合成文本过短，可能会导致模型失败。")
            return text.strip()
        
        # 保存原始文本用于比较
        original_text = text
        
        # 仅处理明显的问题格式，保留更多内容
        cleaned_text = text
        
        # 只处理开头的数字编号，而不是所有行内编号
        if re.match(r'^[\d]+[、.．:：]', cleaned_text):
            cleaned_text = re.sub(r'^[\d]+[、.．:：]\s*', '', cleaned_text)
            
        # 只移除开头的"每日资讯简报"等标题，但保留其他内容
        if re.match(r'^(每日|今日|晨间|晚间).*?(简报|资讯|新闻|播报)', cleaned_text):
            cleaned_text = re.sub(r'^(每日|今日|晨间|晚间).*?(简报|资讯|新闻|播报).*?\n', '', cleaned_text)
        
        # 温和处理标点符号 - 只移除末尾的标点
        punctuation_to_clean = "。？！；…,.!?;:：，"
        cleaned_text = cleaned_text.rstrip(punctuation_to_clean).strip()
        
        # 确保文本不为空
        if not cleaned_text:
            cleaned_text = original_text.strip()  # 至少保留原始文本
            self.log("警告：清理后文本为空，将使用原始文本")
        
        # 记录文本清理前后的变化
        if cleaned_text != original_text:
            self.log(f"文本清理前：【{original_text[:50]}...】")
            self.log(f"文本清理后：【{cleaned_text[:50]}...】")
            # 在日志中显示完整长度，帮助诊断
            self.log(f"清理前长度: {len(original_text)}，清理后长度: {len(cleaned_text)}")
        
        if len(cleaned_text) < 30:
            self.log(f"警告：清理后的文本长度仅为 {len(cleaned_text)} 个字符，这可能会导致合成失败")
            
        return cleaned_text

    def play_audio_file(self, file_path):
        """使用Qt媒体播放器播放合成的音频文件"""
        if not os.path.exists(file_path):
            self.log(f"错误: 音频文件 {file_path} 不存在")
            return False
        
        try:
            # 保存当前播放的文件
            self.current_audio_file = file_path
            
            # 使用媒体播放器播放
            media_content = QMediaContent(QUrl.fromLocalFile(file_path))
            self.media_player.setMedia(media_content)
            self.media_player.play()
            
            # 启用进度条
            self.player_slider.setEnabled(True)
            
            # 更改播放按钮图标为暂停
            self.play_button.setIcon(FluentIcon.PAUSE)
            
            self.log(f"正在播放音频: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            self.log(f"播放音频失败: {str(e)}")
            return False

    def media_state_changed(self, state):
        """媒体播放状态改变时的处理"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setIcon(FluentIcon.PAUSE)
        else:
            self.play_button.setIcon(FluentIcon.PLAY)
    
    def position_changed(self, position):
        """播放位置改变时更新进度条"""
        self.player_slider.setValue(position)
        
        # 更新时间显示
        current_secs = position // 1000
        total_secs = self.media_player.duration() // 1000
        self.player_label.setText(f"{current_secs//60:02d}:{current_secs%60:02d} / {total_secs//60:02d}:{total_secs%60:02d}")
    
    def duration_changed(self, duration):
        """媒体时长改变时更新进度条范围"""
        self.player_slider.setRange(0, duration)
    
    def set_position(self, position):
        """设置播放位置"""
        # 更新时间显示，无需等待position_changed信号
        current_secs = position // 1000
        total_secs = self.media_player.duration() // 1000
        self.player_label.setText(f"{current_secs//60:02d}:{current_secs%60:02d} / {total_secs//60:02d}:{total_secs%60:02d}")
        
        # 不立即设置位置，等待用户松开滑块后再设置
        # 这样可以避免拖动过程中的频繁跳转
    
    def on_play_audio(self):
        """播放按钮点击事件 - 只控制合成音频，不控制示例音频"""
        # 检查播放器状态
        if self.media_player.state() == QMediaPlayer.PlayingState:
            # 如果正在播放，则暂停
            self.media_player.pause()
        elif self.media_player.state() == QMediaPlayer.PausedState:
            # 如果已暂停，则继续播放
            self.media_player.play()
        elif hasattr(self, 'current_audio_file') and os.path.exists(self.current_audio_file):
            # 播放上次合成的文件
            self.play_audio_file(self.current_audio_file)
        else:
            # 没有可播放的合成音频
            InfoBar.warning(
                title="提示",
                content="没有可播放的合成音频，请先合成语音",
                parent=self
            )
            self.log("没有可播放的合成音频")
    
    def play_sample_audio(self, voice_card, file_path):
        """播放示例音频"""
        if not os.path.exists(file_path):
            self.log(f"错误: 音频文件 {file_path} 不存在")
            return False
        
        try:
            # 如果有其他正在播放的示例，先停止它
            if self.current_playing_card and self.current_playing_card != voice_card:
                try:
                    if self.current_playing_card.isVisible() and not sip.isdeleted(self.current_playing_card):
                        self.current_playing_card.set_playing_state(False)
                except (RuntimeError, ReferenceError, Exception):
                    pass  # 对象可能已被删除，忽略错误
                self.sample_player.stop()
            
            # 设置新的播放卡片
            self.current_playing_card = voice_card
            voice_card.set_playing_state(True)
            
            # 播放示例音频
            self.sample_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            self.sample_player.play()
            
            self.log(f"正在播放示例音频: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            self.log(f"播放示例音频失败: {str(e)}")
            return False
    
    def pause_sample_audio(self, voice_card):
        """暂停示例音频"""
        if self.current_playing_card == voice_card:
            try:
                self.sample_player.pause()
                if voice_card.isVisible() and not sip.isdeleted(voice_card):
                    voice_card.set_playing_state(False)
                return True
            except (RuntimeError, ReferenceError, Exception) as e:
                self.log(f"暂停音频失败: {str(e)}")
                return False
        return False
    
    def sample_state_changed(self, state):
        """示例音频播放状态改变时的处理"""
        if state == QMediaPlayer.StoppedState and self.current_playing_card:
            try:
                # 检查卡片对象是否仍然有效
                if self.current_playing_card.isVisible() and not sip.isdeleted(self.current_playing_card):
                    self.current_playing_card.set_playing_state(False)
                self.current_playing_card = None
            except (RuntimeError, ReferenceError, Exception):
                # 对象可能已被删除，安全处理
                self.current_playing_card = None
    
    def filter_voices(self, text):
        """根据搜索框筛选音色"""
        if text:
            self.log(f"搜索音色: {text}")
        self.update_voice_list()  # 根据当前的搜索文本和各种筛选条件重新加载音色列表
    
    def slider_pressed(self):
        """进度条按下事件"""
        # 暂时记录是否正在播放
        self.was_playing = self.media_player.state() == QMediaPlayer.PlayingState
        if self.was_playing:
            self.media_player.pause()  # 按下时暂停播放，使拖动更流畅
    
    def slider_released(self):
        """进度条释放事件"""
        self.media_player.setPosition(self.player_slider.value())  # 设置新位置
        if hasattr(self, 'was_playing') and self.was_playing:
            self.media_player.play()  # 如果之前在播放，则恢复播放

    def browse_prompt_audio(self):
        """Open file dialog to select prompt audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择参考音频文件",
            "",  # Start directory
            "音频文件 (*.wav *.mp3);;WAV 文件 (*.wav);;MP3 文件 (*.mp3);;所有文件 (*.*)"
        )
        if file_path:
            # Basic check if it's wav or mp3, though loading logic handles actual format
            if file_path.lower().endswith(('.wav', '.mp3')):
                self.selected_prompt_audio_path = file_path
                self.prompt_audio_path_edit.setText(file_path)
                self.log(f"已选择参考音频: {file_path}")
            else:
                InfoBar.warning("提示", "请选择有效的WAV或MP3文件", parent=self)
                self.log(f"选择了无效的文件类型: {file_path}")

    # --- New Methods for Chunked Synthesis --- 
    def _concatenate_audio_chunks(self):
        """Uses FFmpeg to concatenate temporary audio files into the final output."""
        if not self.is_chunked_synthesis or not self.temp_audio_files:
            self.log("没有临时文件需要合并。")
            self._cleanup_synthesis("无需合并") # Still cleanup
            return

        if not self.ffmpeg_path:
            self.log("错误：找不到 FFmpeg，无法合并音频块。")
            self._cleanup_synthesis("缺少 FFmpeg") # Cleanup temporary files
            return

        # Create a temporary file list for FFmpeg
        list_file_path = os.path.join(get_resource_path("Resources/output"), "ffmpeg_list.txt")
        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for temp_file in self.temp_audio_files:
                    # Ensure paths are suitable for FFmpeg (use forward slashes maybe?)
                    # Or rely on subprocess handling it correctly on Windows.
                    # Using absolute paths is generally safer.
                    abs_path = os.path.abspath(temp_file)
                    f.write(f"file '{abs_path}'\n") # Use single quotes for paths
            self.log(f"创建 FFmpeg 文件列表: {list_file_path}")
        except Exception as e:
            self.log(f"创建 FFmpeg 文件列表失败: {e}")
            self._cleanup_synthesis("创建列表文件失败")
            return

        # Construct FFmpeg command
        # Use -safe 0 because we are providing absolute paths which might be considered unsafe otherwise.
        command = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file_path,
            '-c', 'copy', # Copy codec, assuming all chunks are wav
            self.final_output_path
        ]

        self.log(f"执行 FFmpeg 命令: {' '.join(command)}")
        concat_success = False
        try:
            # Run FFmpeg
            # Use CREATE_NO_WINDOW on Windows to prevent console popup
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
            
            if result.returncode == 0 and os.path.exists(self.final_output_path):
                self.log(f"FFmpeg 合并成功！最终文件: {self.final_output_path}")
                # Update player with the final merged file
                self.player_file_path = self.final_output_path
                self.play_button.setEnabled(True)
                self.player_slider.setEnabled(True)
                self.player_label.setText(os.path.basename(self.final_output_path))
                InfoBar.success("成功", "分块语音合成并合并完成！", parent=self)
                concat_success = True
            else:
                self.log(f"FFmpeg 合并失败。返回码: {result.returncode}")
                self.log(f"FFmpeg 标准输出:\n{result.stdout}")
                self.log(f"FFmpeg 错误输出:\n{result.stderr}")
                InfoBar.error("失败", "合并音频块失败，请检查日志", parent=self)
        except Exception as e:
            self.log(f"执行 FFmpeg 时发生异常: {e}\n{traceback.format_exc()}")
            InfoBar.error("错误", f"执行 FFmpeg 失败: {e}", parent=self)
        finally:
             # Always attempt cleanup, regardless of concatenation success
             self._cleanup_synthesis("合并完成" if concat_success else "合并失败")
             # Also try to remove the ffmpeg list file
             try:
                 if os.path.exists(list_file_path):
                     os.remove(list_file_path)
             except Exception as e:
                 self.log(f"删除 FFmpeg 列表文件失败: {e}")

    def _cleanup_synthesis(self, reason="未知原因"):
        """Cleans up temporary files and resets synthesis state."""
        self.log(f"开始清理合成状态 ({reason})...")
        
        # Delete temporary audio files
        deleted_count = 0
        failed_count = 0
        if self.temp_audio_files:
            self.log(f"尝试删除 {len(self.temp_audio_files)} 个临时文件...")
            for temp_file in self.temp_audio_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        deleted_count += 1
                        # self.log(f"已删除: {temp_file}") # Optional: verbose logging
                except Exception as e:
                    failed_count += 1
                    self.log(f"删除临时文件失败 {temp_file}: {e}")
            self.log(f"临时文件清理完成：成功删除 {deleted_count} 个，失败 {failed_count} 个。")
        else:
            self.log("没有临时文件需要删除。")
            
        # Reset state variables
        self.is_chunked_synthesis = False
        self.text_chunks = []
        self.current_chunk_index = 0
        self.temp_audio_files = [] # Clear the list
        self.final_output_path = ""
        self.synthesis_thread = None # Clear thread reference

        # Re-enable the synthesis button
        self.synthesize_button.setEnabled(True)
        self.synthesize_button.setText("开始合成")
        self.log("合成状态已重置，按钮已启用。")
    # -----------------------------------------

# 启动应用
if __name__ == '__main__':
    
    # 创建应用实例
    app = QApplication(sys.argv)
    ex = TTSApp()
    ex.show()
    sys.exit(app.exec_())
