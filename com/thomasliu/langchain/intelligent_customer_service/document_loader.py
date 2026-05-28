import os
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_documents() -> str:
    """模拟读取客服知识库文档（实际场景可用 pypdf 读取 PDF）"""
    text = """
        【退换货政策】
        我们的产品支持7天无理由退换货。用户需保证商品包装完好，不影响二次销售。
        退款将在收到退回商品后的3个工作日内原路返还。
        
        【发货说明】
        每日下午4点前的订单当天发货，4点后的订单次日发货。
        合作快递包括顺丰和中通，不支持指定快递。
        
        【会员权益】
        注册会员可享受全场98折优惠。
        金牌会员（年消费满1000元）享受全场9折及免费上门取件退货服务。
        """
    return text.strip()


def split_text(text: str, chunk_size: int = 100, chunk_overlap: int = 20) -> list[str]:
    """
    将文本切分为块，防止语义被切断

    Args:
        text: 输入文本
        chunk_size: 每个块的最大字符数
        chunk_overlap: 块之间的重叠字符数

    Returns:
        切分后的文本块列表
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(text)
    print(f"文档共切分为 {len(chunks)} 个块")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n块 {i}:")
        print(chunk)
    return chunks



