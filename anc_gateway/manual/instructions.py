from __future__ import annotations

from anc_gateway.manual.schemas import ManualVendorPlatform


def build_manual_instructions(
    platform: ManualVendorPlatform,
    compiled_prompt: str,
    visual_anchor_uri: str | None,
) -> str:
    anchor_text = (
        f"如果页面支持参考图或首帧，请手动上传这个 visual_anchor_uri 对应图片：{visual_anchor_uri}。"
        if visual_anchor_uri
        else "如果页面支持参考图或首帧，可以按需手动上传本地参考图。"
    )
    if platform == ManualVendorPlatform.JIMENG_WEB:
        return (
            "打开即梦网页端，选择视频生成。"
            f"复制以下 compiled_prompt 到提示词输入框：{compiled_prompt}。"
            f"{anchor_text}"
            "生成后下载视频，回到本系统填写 result_video_uri 或本地文件路径。"
            "不要模拟登录，不要抓取 cookie，不要使用浏览器自动化绕过平台限制。"
        )
    if platform == ManualVendorPlatform.GEMINI_FLOW:
        return (
            "打开 Gemini / Flow，新建视频生成。"
            f"复制以下 compiled_prompt 到提示词输入框：{compiled_prompt}。"
            f"{anchor_text}"
            "生成并下载视频后，回填 result_video_uri 或本地文件路径。"
            "不要模拟登录，不要抓取 cookie，不要使用浏览器自动化绕过平台限制。"
        )
    return (
        "打开目标视频生成网页，手动复制 prompt。"
        f"Prompt：{compiled_prompt}。"
        f"{anchor_text}"
        "手动生成视频并下载，回到本系统填写 result_video_uri 或本地文件路径。"
        "不要模拟登录，不要抓取 cookie，不要使用浏览器自动化。"
    )
