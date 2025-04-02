import os
import torch
import soundfile as sf
from pathlib import Path
import time
from sparktts.models.audio_tokenizer import BiCodecTokenizer
from cli.SparkTTS import SparkTTS

# 设置参数
model_dir = "pretrained_models/Spark-TTS-0.5B"
prompt_speech_path = r"E:\code\Spark-TTS\example\results\20250225113521.wav"
prompt_text = "网红猫又又去世​：24岁二次元博主因抑郁症离世，粉丝悼念\"愿天堂没有病痛\"，心理健康再引关注。"
target_text = "每日资讯简报\n" \
              "1、女子离婚嫁妆纠纷案：法院判决仅支持部分诉求，因嫁妆价值未超彩礼且部分损毁，引发婚嫁财产法律争议。\n" \
              "2、网红猫又又去世​：24岁二次元博主因抑郁症离世，粉丝悼念\"愿天堂没有病痛\"，心理健康再引关注。\n" \
              "3、小女孩跳\"科目三\"扭伤：医生提醒儿童舞蹈需谨慎，避免高难度动作引发关节损伤，建议科学指导。\n" \
              "4、河南高速车祸现场：多车相撞致拥堵，雪天路滑成主因，提醒司机减速慢行，保持车距。\n" \
              "5、苹果Vision Pro评测：科技媒体指出其优缺点并存，沉浸体验惊艳但价格高昂、应用生态待完善，市场前景引关注。"
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
