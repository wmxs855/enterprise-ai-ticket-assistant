# 在线模型验证准备

当前项目没有配置用户密钥，因此在线调用尚未执行。需要验证时，应由密钥所有者在自己的终端中临时设置环境变量。

## 安全原则

- 不要把密钥发送到聊天消息。
- 不要把密钥写入 Python 源代码。
- 不要把密钥写入会提交到 Git 的文件。
- 不要在日志、截图和演示视频中显示密钥。
- 怀疑密钥泄露时，应立即在服务平台撤销并重新创建。

## PowerShell 临时设置方式

下面的设置只对当前终端窗口有效，关闭窗口后会消失：

```powershell
$env:OPENAI_API_KEY = "在这里填写自己的密钥"
$env:OPENAI_MODEL = "填写账户实际可用的模型名称"
```

`OPENAI_API_KEY` 是 OpenAI 应用程序编程接口密钥的标准环境变量名称；`OPENAI_MODEL` 是本项目用于指定模型名称的环境变量。

不要照抄示例占位文字。模型名称必须以用户账户实际可用范围为准。

## 只检查是否已经设置

下面的命令只返回真或假，不显示密钥内容：

```powershell
Test-Path Env:OPENAI_API_KEY
Test-Path Env:OPENAI_MODEL
```

## 执行一次在线问答

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m src.answer_generator "银行卡退款到账需要多久" --mode openai
```

运行后需要核对答案是否保留原文中的数字、是否包含程序附加的来源，以及模型服务异常时是否能够安全回退。

