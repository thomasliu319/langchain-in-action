import torch
import torch.nn as nn
import torch.optim as optim
from torchtext.datasets import AG_NEWS
from torchtext.data.utils import get_tokenizer
from torchtext.vocab import build_vocab_from_iterator
from torch.utils.data import DataLoader
import torch.nn.functional as F

EMBEDDING_DIM = 128
HIDDEN_DIM = 256
NUM_HEADS = 8
NUM_ENCODER_LAYERS = 3
NUM_CLASSES = 4
BATCH_SIZE = 16
EPOCHS = 3
LR = 0.001


def yield_tokens(data_iter):
    for _, text in data_iter:
        yield tokenizer(text)


tokenizer = get_tokenizer("basic_english")
train_iter = AG_NEWS(split="train")

vocab = build_vocab_from_iterator(yield_tokens(train_iter), specials=["<unk>"])
vocab.set_default_index(vocab["<unk>"])


def collate_batch(batch):
    labels, texts = zip(*batch)
    text_tensor = torch.nn.utils.rnn.pad_sequence(
        [torch.tensor(vocab(tokenizer(text))) for text in texts], padding_value=0
    )
    return text_tensor, torch.tensor(labels)


train_iter = AG_NEWS(split="train")
train_loader = DataLoader(
    train_iter, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_batch
)


class TransformerModel(nn.Module):
    def __init__(self, num_classes):
        super(TransformerModel, self).__init__()
        self.embedding = nn.Embedding(len(vocab), EMBEDDING_DIM)
        self.transformer_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=EMBEDDING_DIM, nhead=NUM_HEADS, dim_feedforward=HIDDEN_DIM
            ),
            num_layers=NUM_ENCODER_LAYERS,
        )
        self.fc = nn.Linear(EMBEDDING_DIM, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(1, 0, 2)
        x = self.transformer_encoder(x)
        x = x.mean(dim=1)
        x = self.fc(x)
        return x


if __name__ == "__main__":
    model = TransformerModel(NUM_CLASSES)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)

    for epoch in range(EPOCHS):
        model.train()
        for batch_idx, (texts, labels) in enumerate(train_loader):
            optimizer.zero_grad()
            outputs = model(texts)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            if batch_idx % 100 == 0:
                print(
                    f"Epoch [{epoch + 1}/{EPOCHS}], Step [{batch_idx}/{len(train_loader)}], Loss: {loss.item():.4f}"
                )

    print("Training complete.")
