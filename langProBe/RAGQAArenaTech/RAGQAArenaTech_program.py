import dspy
import torch
from pathlib import Path
from litellm import embedding as Embed
import ujson
import os
import requests
import langProBe.dspy_program as dspy_program
from langProBe.dspy_program import LangProBeDSPyMetaProgram, deduplicate
from .RAGQAArenaTech_utils import GenerateSearchQuery


class SimplifiedBaleen(LangProBeDSPyMetaProgram, dspy.Module):
    def __init__(self, num_docs=5, max_hops=2):
        Path("langProBe/RAGQAArenaTech/data").mkdir(exist_ok=True)

        urls = [
            "https://huggingface.co/datasets/colbertv2/lotte_passages/resolve/main/technology/test_collection.jsonl",
            "https://huggingface.co/dspy/cache/resolve/main/index.pt",
        ]

        for url in urls:
            filename = os.path.basename(url)
            filepath = os.path.join("langProBe/RAGQAArenaTech/data", filename)
            remote_size = int(
                requests.head(url, allow_redirects=True).headers.get(
                    "Content-Length", 0
                )
            )
            local_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

            if local_size != remote_size:
                print(f"Downloading '{filename}'...")
                with requests.get(url, stream=True) as r, open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        print("Download completed")

        self.max_hops = max_hops
        self.num_docs = num_docs
        self.respond = dspy.ChainOfThought("context, question -> response")
        self.max_characters = 4000
        with open("langProBe/RAGQAArenaTech/data/test_collection.jsonl") as f:
            self.corpus = [ujson.loads(line) for line in f]
        self.index = torch.load(
            "langProBe/RAGQAArenaTech/data/index.pt", weights_only=True
        )

        self.generate_query = [
            dspy.ChainOfThought(GenerateSearchQuery) for _ in range(self.max_hops)
        ]

    def search(self, query, k=5):
        query_embedding = torch.tensor(
            Embed(input=query, model="text-embedding-3-small").data[0]["embedding"]
        )
        topk_scores, topk_indices = torch.matmul(self.index, query_embedding).topk(k)
        topK = [
            dict(score=score.item(), **self.corpus[idx])
            for idx, score in zip(topk_indices, topk_scores)
        ]
        return [doc["text"][: self.max_characters] for doc in topK]

    def forward(self, question):
        context = []
        for hop in range(self.max_hops):
            query = self.generate_query[hop](context=context, question=question).query
            passages = self.search(query, k=self.num_docs)
            context = deduplicate(context + passages)
        return self.respond(context=context, question=question)


class RAG(LangProBeDSPyMetaProgram, dspy.Module):
    def __init__(self, num_docs=5):
        Path("langProBe/RAGQAArenaTech/data").mkdir(exist_ok=True)

        urls = [
            "https://huggingface.co/datasets/colbertv2/lotte_passages/resolve/main/technology/test_collection.jsonl",
            "https://huggingface.co/dspy/cache/resolve/main/index.pt",
        ]

        for url in urls:
            filename = os.path.basename(url)
            filepath = os.path.join("langProBe/RAGQAArenaTech/data", filename)
            remote_size = int(
                requests.head(url, allow_redirects=True).headers.get(
                    "Content-Length", 0
                )
            )
            local_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

            if local_size != remote_size:
                print(f"Downloading '{filename}'...")
                with requests.get(url, stream=True) as r, open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        print("Download completed")

        self.num_docs = num_docs
        self.respond = dspy.ChainOfThought("context, question -> response")
        self.max_characters = 4000
        with open("langProBe/RAGQAArenaTech/data/test_collection.jsonl") as f:
            self.corpus = [ujson.loads(line) for line in f]
        self.index = torch.load(
            "langProBe/RAGQAArenaTech/data/index.pt", weights_only=True
        )

    def search(self, query, k=5):
        query_embedding = torch.tensor(
            Embed(input=query, model="text-embedding-3-small").data[0]["embedding"]
        )
        topk_scores, topk_indices = torch.matmul(self.index, query_embedding).topk(k)
        topK = [
            dict(score=score.item(), **self.corpus[idx])
            for idx, score in zip(topk_indices, topk_scores)
        ]
        return [doc["text"][: self.max_characters] for doc in topK]

    def forward(self, question):
        context = self.search(question, k=self.num_docs)
        return self.respond(context=context, question=question)


basic_signature = "question -> response"

RAGQAPredict = dspy_program.Predict(basic_signature)
RAGQACoT = dspy_program.CoT(basic_signature)
RAGQARAG = RAG()
RAGQASimplifiedBaleen = SimplifiedBaleen()
RAGQAGeneratorCriticFuser = dspy_program.GeneratorCriticFuser(basic_signature)
RAGQAGeneratorCriticFuser_20 = dspy_program.GeneratorCriticFuser(basic_signature, n=20)
RAGQAGeneratorCriticRanker = dspy_program.GeneratorCriticRanker(basic_signature)
RAGQAGeneratorCriticRanker_20 = dspy_program.GeneratorCriticRanker(
    basic_signature, n=20
)
