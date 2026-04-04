--------------------------------------------------------------------------------------------------------------


import torch
import torch.nn as nn
import torch.optim as optim
from torchtext.datasets import AG_NEWS
from torchtext.data.utils import get_tokenizer
from torchtext.vocab import build_vocab_from_iterator
from torch.utils.data import DataLoader
import torch.nn.functional as F

# 定义超参数
EMBEDDING_DIM = 128
HIDDEN_DIM = 256
NUM_HEADS = 8
NUM_ENCODER_LAYERS = 3
NUM_CLASSES = 4
BATCH_SIZE = 16
EPOCHS = 3
LR = 0.001

# 1. 准备数据
def yield_tokens(data_iter):
    for _, text in data_iter:
        yield tokenizer(text)

tokenizer = get_tokenizer('basic_english')
train_iter = AG_NEWS(split='train')

vocab = build_vocab_from_iterator\
(yield_tokens(train_iter), specials=["<unk>"])
vocab.set_default_index(vocab["<unk>"])

# 数据加载器
def collate_batch(batch):
    labels, texts = zip(*batch)
    text_tensor = torch.nn.utils.rnn.pad_sequence([torch.tensor(vocab(tokenizer(text))) \
for text in texts], padding_value=0)
    return text_tensor, torch.tensor(labels)

train_iter = AG_NEWS(split='train')
train_loader = DataLoader(train_iter, batch_size=BATCH_SIZE, \
shuffle=True, collate_fn=collate_batch)

# 2. 定义 Transformer 模型
class TransformerModel(nn.Module):
    def __init__(self, num_classes):
        super(TransformerModel, self).__init__()
        self.embedding = nn.Embedding(len(vocab), EMBEDDING_DIM)
        self.transformer_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=EMBEDDING_DIM, nhead=NUM_HEADS, dim_feedforward=HIDDEN_DIM),
            num_layers=NUM_ENCODER_LAYERS
        )
        self.fc = nn.Linear(EMBEDDING_DIM, num_classes)

    def forward(self, x):
        # 输入 x 的形状为 (seq_length, batch_size)
        x = self.embedding(x) 
 # (seq_length, batch_size, embedding_dim)
        x = x.permute(1, 0, 2)  
# 转换为 (batch_size, seq_length, embedding_dim)
        x = self.transformer_encoder(x)  
# (batch_size, seq_length, embedding_dim)
        x = x.mean(dim=1)  # 池化
        x = self.fc(x)  # 分类
        return x

# 3. 初始化模型、损失函数和优化器
model = TransformerModel(NUM_CLASSES)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=LR)

# 4. 训练模型
for epoch in range(EPOCHS):
    model.train()
    for batch_idx, (texts, labels) in enumerate(train_loader):
        optimizer.zero_grad()
        outputs = model(texts)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        if batch_idx % 100 == 0:
            print(f'Epoch [{epoch+1}/{EPOCHS}], \
Step [{batch_idx}/{len(train_loader)}], Loss: {loss.item():.4f}')

print("Training complete.")


--------------------------------------------------------------------------------------------------------------


# 导入必要的库
from langchain.chains import SequentialChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory

# 初始化 OpenAI 模型
llm = OpenAI(temperature=0.7)

# 定义意图识别的 Prompt 模板
intent_prompt = PromptTemplate(
    input_variables=["input_text"],
    template="请根据以下输入识别用户意图：{input_text}"
)

# 定义实体提取的 Prompt 模板
entity_prompt = PromptTemplate(
    input_variables=["intent", "input_text"],
    template="根据用户的意图 '{intent}'，从以下输入中提取相关实体：{input_text}"
)

# 定义动作确定的 Prompt 模板
action_prompt = PromptTemplate(
    input_variables=["intent", "entities"],
    template="根据意图 '{intent}' 和提取的实体 '{entities}'，确定要执行的操作。"
)

# 定义响应生成的 Prompt 模板
response_prompt = PromptTemplate(
    input_variables=["action"],
    template="根据确定的动作 '{action}' 生成用户的响应。"
)

# 创建各个任务节点的链
intent_chain = SequentialChain(
    llm=llm,
    prompt=intent_prompt,
    output_key="intent",
    memory=ConversationBufferMemory()
)

entity_chain = SequentialChain(
    llm=llm,
    prompt=entity_prompt,
    output_key="entities",
    memory=ConversationBufferMemory()
)

action_chain = SequentialChain(
    llm=llm,
    prompt=action_prompt,
    output_key="action",
    memory=ConversationBufferMemory()
)

response_chain = SequentialChain(
    llm=llm,
    prompt=response_prompt,
    output_key="response",
    memory=ConversationBufferMemory()
)

# 定义顺序链，按顺序执行各个任务节点
sequential_chain = SequentialChain(
    chains=[intent_chain, entity_chain, action_chain, response_chain],
    input_variables=["input_text"],
    output_variables=["response"],
    memory=ConversationBufferMemory()
)

# 测试顺序链
if __name__ == "__main__":
    # 示例输入文本
    input_text = "我想查询北京的天气。"
    
    # 运行顺序链
    final_response = sequential_chain.run({"input_text": input_text})
    
    print("\n最终生成的响应:", final_response["response"])


--------------------------------------------------------------------------------------------------------------


# 导入必要的库
from langchain.chains import SequentialChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory

# 初始化 OpenAI 模型
llm = OpenAI(temperature=0.7)
# 初始化内存模块
memory = ConversationBufferMemory()

# 定义意图识别的 Prompt 模板
intent_prompt = PromptTemplate(
    input_variables=["input_text"],
    template="请根据以下输入识别用户意图：{input_text}"
)

# 定义实体提取的 Prompt 模板
entity_prompt = PromptTemplate(
    input_variables=["intent", "input_text"],
    template="根据用户的意图 '{intent}'，从以下输入中提取相关实体：{input_text}"
)

# 定义动作确定的 Prompt 模板
action_prompt = PromptTemplate(
    input_variables=["intent", "entities"],
    template="根据意图 '{intent}' 和提取的实体 '{entities}'，确定要执行的操作。"
)

# 定义响应生成的 Prompt 模板
response_prompt = PromptTemplate(
    input_variables=["action"],
    template="根据确定的动作 '{action}' 生成用户的响应。"
)

# 创建各个任务节点的链
intent_chain = SequentialChain(
    llm=llm,
    prompt=intent_prompt,
    output_key="intent",
    memory=memory
)

entity_chain = SequentialChain(
    llm=llm,
    prompt=entity_prompt,
    output_key="entities",
    memory=memory
)

action_chain = SequentialChain(
    llm=llm,
    prompt=action_prompt,
    output_key="action",
    memory=memory
)

response_chain = SequentialChain(
    llm=llm,
    prompt=response_prompt,
    output_key="response",
    memory=memory
)

# 定义顺序链，按顺序执行各个任务节点
sequential_chain = SequentialChain(
    chains=[intent_chain, entity_chain, action_chain, response_chain],
    input_variables=["input_text"],
    output_variables=["response"],
    memory=memory
)

# 测试顺序链
if __name__ == "__main__":
    # 示例输入文本
    input_text = "我想查询北京的天气。"
    
    # 运行顺序链
    final_response = sequential_chain.run({"input_text": input_text})
    
    print("\n最终生成的响应:", final_response["response"])

    # 测试多轮对话，验证内存功能
    input_text_2 = "那明天呢？"
    final_response_2 = sequential_chain.run({"input_text": input_text_2})
    print("\n最终生成的响应 (第二轮):", final_response_2["response"])
memory = ConversationBufferMemory()
intent_chain = SequentialChain(
    llm=llm,
    prompt=intent_prompt,
    output_key="intent",
    memory=memory
)


--------------------------------------------------------------------------------------------------------------


from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# 初始化OpenAI模型
llm = OpenAI(api_key="YOUR_API_KEY", model="text-davinci-003")

# 提示词模板设计：生成企业创新的简短描述
prompt_template = """
请用简明扼要的语言描述企业创新的重要性，并说明它如何影响企业的长远发展。
"""

# 构建提示词对象
prompt = PromptTemplate(
    input_variables=[],
    template=prompt_template
)

# 构建LangChain任务链
chain = LLMChain(llm=llm, prompt=prompt)

# 执行任务链，获取生成结果
result = chain.run()

# 输出结果
print("生成的企业创新描述：")
print(result)


--------------------------------------------------------------------------------------------------------------



from langchain.llms import OpenAI
llm = OpenAI(api_key="YOUR_API_KEY", model="text-davinci-003")
from langchain.prompts import PromptTemplate
prompt_template = PromptTemplate(
    input_variables=[],
    template="请简要描述企业创新的重要性。"
)
from langchain.chains import LLMChain
chain = LLMChain(llm=llm, prompt=prompt_template)
result = chain.run()
from langchain.memory import Memory
memory = Memory()
prompt_template = PromptTemplate(
    input_variables=["product_name", "features"],
    template="请介绍产品{name}，其特点为{features}。"
)
chain = LLMChain(llm=llm, prompt=prompt_template)
result = chain.run()
print(result)
