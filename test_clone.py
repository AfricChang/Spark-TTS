import os
import torch
import soundfile as sf
from pathlib import Path
import time
from sparktts.models.audio_tokenizer import BiCodecTokenizer
from cli.SparkTTS import SparkTTS

# 设置参数
model_dir = "pretrained_models/Spark-TTS-0.5B"
prompt_speech_path = r"E:\code\Spark-TTS\test\智友-1741423093665-087106.wav"
prompt_text = "网红猫又又去世​：24岁二次元博主因抑郁症离世，粉丝悼念“愿天堂没有病痛”，心理健康再引关注。"
target_text = "每日资讯简报" \
"1、缅甸强震已致1700死3400伤，专家称地震破坏力极大，像巨刀切入地球。\n"\
"2、邮储银行拟向财政部等发行A股股票，融资1300亿元。\n"\
"3、美国回应中方审查李嘉诚出售港口事件，表示关注交易合规性。\n"\
"4、华为折叠屏手机开售10分钟售罄，市场需求旺盛，供不应求。\n"\
"5、四大银行公布融资方案，合计募资5200亿元，支持经济发展。\n"\
"6、特朗普：必须拿下格陵兰岛 军事或经济手段皆可。\n"\
"7、利率3%以下银行消费贷或被叫停，市场受影响，监管加强。\n"\
"8、66岁柏林大妈自然受孕产下第10子，医学奇迹引关注。  \n"\
"9、美军双航母集结中东，意图威慑伊朗，地区局势紧张。\n"\
"10、乐事薯片含TBHQ，符合国标但过量有风险，消费者需谨慎。\n"\
"11、以军承认在加沙南部误向救护车和消防车开火。\n"\
"12、湖北宜昌火锅店老板因在底料中加罂粟被判刑并终身禁业。\n"\
"13、中国银行四川省分行原党委书记、行长葛春尧涉嫌违纪违法被查。\n"\
"14、汤加海域发生7.3级地震。\n"\
"15、男子唐阳因精神分裂症被家人送医，符合出院标准，但17年未被家人接回。\n"
save_dir = r"E:\code\Spark-TTS\example\results"
device = "cuda:0"  # 或 "cpu" 进行对比测试

# 确保输出目录存在
os.makedirs(save_dir, exist_ok=True)

print(f"使用设备: {device}")
print(f"模型目录: {model_dir}")
print(f"参考音频: {prompt_speech_path}")
print(f"输出目录: {save_dir}")

# 加载模型
print("正在加载模型...")
model = SparkTTS(
    model_dir=model_dir,
    device=device,
)

# 直接测试音频分词器
# print("\n===== 测试音频分词器 =====")
# audio_tokenizer = BiCodecTokenizer(model_dir=Path(model_dir), device=device)
# print(f"音频分词器已加载到设备: {audio_tokenizer.device}")

# 检查参考音频
# print("\n===== 分析参考音频 =====")
# wav, ref_wav = audio_tokenizer.process_audio(prompt_speech_path)
# print(f"原始音频长度: {len(wav)}")
# print(f"参考音频张量形状: {ref_wav.shape}")

# 提取特征
# print("\n===== 提取音频特征 =====")
# feat = audio_tokenizer.extract_wav2vec2_features(wav)
# print(f"提取的特征形状: {feat.shape}")

# 创建批次
# print("\n===== 创建批次 =====")
# batch = {
#     "wav": torch.from_numpy(wav).unsqueeze(0).float().to(device),
#     "ref_wav": ref_wav.to(device),
#     "feat": feat.to(device),
# }
# print(f"批次中wav形状: {batch['wav'].shape}")
# print(f"批次中ref_wav形状: {batch['ref_wav'].shape}")
# print(f"批次中feat形状: {batch['feat'].shape}")

# 进行分词
# print("\n===== 执行分词 =====")
# try:
#     global_tokens, semantic_tokens = audio_tokenizer.model.tokenize(batch)
#     print(f"global_tokens形状: {global_tokens.shape}")
#     print(f"semantic_tokens形状: {semantic_tokens.shape}")
    
#     # 检查semantic_tokens是否为空
#     if semantic_tokens.size(1) == 0:
#         print("警告: semantic_tokens是空的，这可能是问题所在!")
#         torch.save(batch, f"{save_dir}/problem_batch.pt")
#         print(f"已保存问题批次到: {save_dir}/problem_batch.pt")
    
#     # 尝试重构测试，但使用正确的形状
#     if semantic_tokens.size(1) > 0:
#         print("\n===== 测试重构 =====")
#         # 检查detokenize前的张量形状
#         print(f"送入detokenize前 - Global tokens形状: {global_tokens.shape}")
#         print(f"送入detokenize前 - Semantic tokens形状: {semantic_tokens.shape}")
        
#         # 确保形状正确 - 在需要时调整
#         # 注意：根据你的错误信息，可能需要调整这些形状
#         if global_tokens.dim() == 2:
#             global_tokens_adj = global_tokens.unsqueeze(1)
#         else:
#             global_tokens_adj = global_tokens
            
#         try:
#             wav_rec = audio_tokenizer.detokenize(global_tokens_adj, semantic_tokens)
#             sf.write(f"{save_dir}/reconstructed.wav", wav_rec, 16000)
#             print(f"重构音频已保存到: {save_dir}/reconstructed.wav")
#         except Exception as e:
#             print(f"重构出错: {e}")
#             print("保存tokens以供后续分析...")
#             torch.save({"global_tokens": global_tokens, "semantic_tokens": semantic_tokens}, 
#                       f"{save_dir}/tokens.pt")
# except Exception as e:
#     print(f"分词过程出错: {e}")

# 尝试语音合成
print("\n===== 尝试语音合成 =====")
try:
    print("使用模型推理...")
    output_file = f"{save_dir}/synthesized.wav"
    
    # 查看inference方法的参数列表
    import inspect
    print("SparkTTS.inference方法的参数:", 
          inspect.signature(model.inference))
    
    # 记录开始时间
    start_time = time.time()
    
    # 使用合适的参数调用inference
    wav = model.inference(
        text=target_text,
        prompt_text=prompt_text,
        prompt_speech_path=prompt_speech_path
    )
    
    # 记录结束时间
    end_time = time.time()
    synthesis_time = end_time - start_time
    print(f"合成耗时: {synthesis_time:.2f} 秒") # <-- 打印耗时
    
    # 手动保存生成的音频
    if wav is not None:
        sf.write(output_file, wav, 16000)
        print(f"合成音频已保存到: {output_file}")
except Exception as e:
    print(f"语音合成出错: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")
