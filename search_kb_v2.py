#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
search_kb_v2.py
========================================================

UX Research Knowledge Base Search Engine V2

Author : ChatGPT
Version: 2.0

Features
--------
✓ jsDelivr CDN
✓ GitHub Raw Fallback
✓ Local Cache
✓ Query Expansion (CN + EN)
✓ Phrase Boost
✓ Category Weight
✓ Better Ranking
✓ Context Snippet
✓ Duplicate Removal
✓ Hybrid Search Ready
✓ JSON Output

Compatible with:
- GitHub Actions
- kb_bundle.json
- jsDelivr CDN

========================================================
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.request

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Set



########################################################
# Configuration
########################################################

GITHUB_OWNER = "CCC-ybw"
GITHUB_REPO = "ux-research-kb"
GITHUB_BRANCH = "main"

JSDELIVR_URL = (
    f"https://cdn.jsdelivr.net/gh/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}/kb_bundle.json"
)

RAW_URL = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}/"
    f"{GITHUB_BRANCH}/kb_bundle.json"
)

CACHE_TTL = 1800

SKILL_DIR = (
    Path.home()
    / ".workbuddy"
    / "skills"
    / "ux-research-kb"
)

CACHE_DIR = SKILL_DIR / "cache"



########################################################
# Logging
########################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

logger = logging.getLogger("kb-search")



########################################################
# Models
########################################################

@dataclass
class SearchResult:

    file: str

    title: str

    category: str

    score: float

    snippet: str

    context_before: str

    context_after: str

    github_url: str

    char_count: int



########################################################
# Utils
########################################################

def md5(text: str) -> str:

    return hashlib.md5(
        text.encode("utf-8")
    ).hexdigest()



def http_get(url: str, timeout: int = 20) -> str:

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ux-research-kb-v2"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=timeout
    ) as resp:

        return resp.read().decode(
            "utf-8",
            errors="replace"
        )



########################################################
# Cache
########################################################

class Cache:

    def __init__(self):

        CACHE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

    def path(self, key: str):

        return CACHE_DIR / f"{md5(key)[:12]}.json"

    def load(self, key: str):

        p = self.path(key)

        if not p.exists():

            return None

        age = time.time() - p.stat().st_mtime

        if age > CACHE_TTL:

            return None

        try:

            with open(
                p,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:

            return None

    def save(self, key: str, obj):

        with open(
            self.path(key),
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                obj,
                f,
                ensure_ascii=False
            )


cache = Cache()



########################################################
# Bundle Loader
########################################################

class BundleLoader:

    def load(
        self,
        refresh=False
    ):

        key = "bundle"

        if not refresh:

            cached = cache.load(key)

            if cached:

                logger.info("Use cache")

                return cached

        for url in [
            JSDELIVR_URL,
            RAW_URL
        ]:

            try:

                logger.info(f"Downloading {url}")

                bundle = json.loads(
                    http_get(url)
                )

                cache.save(
                    key,
                    bundle
                )

                return bundle

            except Exception as e:

                logger.warning(e)

        cached = cache.load(key)

        if cached:

            logger.warning(
                "Network failed, use cache."
            )

            return cached

        raise RuntimeError(
            "Cannot download kb_bundle.json"
        )
########################################################
# Synonym Engine
########################################################

SYNONYMS = {

    # Supplier
    "supplier": [
        "supplier",
        "vendor",
        "manufacturer",
        "factory",
        "producer",
        "oem",
        "供应商",
        "厂家",
        "工厂",
        "制造商",
        "OEM"
    ],

    # RFQ
    "rfq": [
        "rfq",
        "quotation",
        "quote",
        "pricing",
        "price",
        "询价",
        "报价",
        "价格",
        "报价单"
    ],

    # Procurement
    "procurement": [
        "procurement",
        "purchasing",
        "purchase",
        "buying",
        "sourcing",
        "采购",
        "购买",
        "寻源",
        "采购流程"
    ],

    # AI
    "ai": [
        "ai",
        "artificial intelligence",
        "chatgpt",
        "copilot",
        "llm",
        "gpt",
        "人工智能",
        "大模型",
        "智能"
    ],

    # Persona
    "persona": [
        "persona",
        "buyer persona",
        "用户画像",
        "买家画像",
        "画像"
    ],

    # Journey
    "journey": [
        "journey",
        "workflow",
        "process",
        "流程",
        "采购流程",
        "用户旅程"
    ],

    # Insight
    "insight": [
        "insight",
        "finding",
        "learning",
        "洞察",
        "发现",
        "结论"
    ]
}


########################################################
# Category Weight
########################################################

CATEGORY_WEIGHT = {

    "买家访谈": 1.25,

    "供应商访谈": 1.15,

    "研究报告": 1.05,

    "其他": 1.00

}


########################################################
# Query Expander
########################################################

class QueryExpander:

    def __init__(self):

        self.synonyms = SYNONYMS

    def expand(
        self,
        query: str
    ) -> List[str]:

        expanded: Set[str] = set()

        expanded.add(query)

        lower = query.lower()

        # exact keyword mapping
        for key, values in self.synonyms.items():

            if key in lower:

                expanded.update(values)

            for word in values:

                if word.lower() in lower:

                    expanded.update(values)

        # split by spaces
        words = re.split(r"[\s,/，。；;]+", query)

        for w in words:

            lw = w.lower()

            if lw in self.synonyms:

                expanded.update(
                    self.synonyms[lw]
                )

            for key, values in self.synonyms.items():

                if lw in [v.lower() for v in values]:

                    expanded.update(values)

        # remove empty
        expanded = {

            x.strip()

            for x in expanded

            if x.strip()

        }

        return sorted(expanded)


query_expander = QueryExpander()


########################################################
# Tokenizer
########################################################

TOKEN_SPLIT_RE = re.compile(

    r"[，。！？、；：,.!?;:()\[\]{}<>@#$%^&*+=|\\/'`~\s]+"

)
def tokenize(text: str) -> List[str]:

    if not text:

        return []


    text = text.lower()


    # 中英文分离
    tokens = []


    # 英文单词
    english = re.findall(
        r"[a-zA-Z]{3,}",
        text
    )


    tokens.extend(
        english
    )


    # 中文词块
    chinese = re.findall(
        r"[\u4e00-\u9fff]{2,}",
        text
    )


    tokens.extend(
        chinese
    )


    return tokens

########################################################
# Ranking Engine
########################################################
########################################################
# Ranking Engine V2.1
########################################################

class RankingEngine:


    def __init__(self):

        self.category_weight = CATEGORY_WEIGHT


        # 高价值采购领域词
        self.domain_keywords = [

            "procurement",
            "purchasing",
            "sourcing",
            "supplier",
            "vendor",
            "manufacturer",
            "factory",
            "rfq",
            "quotation",
            "quote",
            "采购",
            "采购流程",
            "供应商",
            "厂家",
            "工厂",
            "寻源",
            "询价",
            "报价"

        ]



        # AI相关词
        # 权重降低，避免普通AI命中污染结果

        self.ai_keywords = [

            "ai",
            "artificial intelligence",
            "chatgpt",
            "copilot",
            "gpt",
            "llm",
            "人工智能",
            "大模型"

        ]



    def normalize_text(
        self,
        text: str
    ):

        return text.lower()



    def phrase_score(
        self,
        query,
        text
    ):


        if not query:

            return 0



        q = query.lower()

        t = text.lower()



        # 完整问题命中

        if q in t:

            return 5



        return 0



    def domain_score(
        self,
        text
    ):


        score = 0


        t = text.lower()


        for word in self.domain_keywords:


            if word.lower() in t:

                score += 0.15



        return min(
            score,
            2
        )



    def ai_score(
        self,
        text
    ):


        """
        AI关键词只作为辅助。
        避免 ai / gpt 出现一次造成误判。
        """


        score = 0


        t = text.lower()


        for word in self.ai_keywords:


            if word.lower() in t:

                score += 0.05



        return min(
            score,
            0.5
        )



    def keyword_score(
        self,
        query_terms,
        text
    ):


        if not query_terms:

            return 0



        text_tokens = set(
            tokenize(text)
        )


        matched = 0



        for term in query_terms:


            term = term.lower()


            # 忽略过短token

            if len(term) <= 2:

                continue



            if term in text_tokens:

                matched += 1



        return (
            matched /
            max(
                len(query_terms),
                1
            )
        )



    def title_score(
        self,
        query_terms,
        title
    ):


        if not title:

            return 0



        title = title.lower()


        score = 0



        for term in query_terms:


            if len(term) <= 2:

                continue



            if term.lower() in title:

                score += 0.5



        return min(
            score,
            3
        )



    def calculate(
        self,
        query,
        expanded_queries,
        text,
        title,
        category
    ):


        score = 0



        combined_text = (
            title
            +
            "\n"
            +
            text
        )



        # --------------------
        # 1. 原始query精准匹配
        # --------------------

        score += (
            self.phrase_score(
                query,
                combined_text
            )
        )



        # --------------------
        # 2. 标题权重
        # --------------------

        terms = []


        for q in expanded_queries:

            terms.extend(
                tokenize(q)
            )


        terms = list(
            set(terms)
        )



        score += (
            self.title_score(
                terms,
                title
            )
        )



        # --------------------
        # 3. 采购领域权重
        # --------------------

        score += (
            self.domain_score(
                combined_text
            )
        )



        # --------------------
        # 4. AI辅助权重
        # --------------------

        score += (
            self.ai_score(
                combined_text
            )
        )



        # --------------------
        # 5. Keyword overlap
        # --------------------

        score += (
            self.keyword_score(
                terms,
                combined_text
            )
            *
            2
        )



        # --------------------
        # 6. Category Weight
        # --------------------

        weight = (
            self.category_weight.get(
                category,
                1.0
            )
        )


        score *= weight



        # Normalize

        return round(

            min(
                score / 8,
                1
            ),

            4

        )



ranking_engine = RankingEngine()
########################################################
# File Classifier
########################################################

class FileClassifier:


    def classify(
        self,
        filename: str
    ) -> str:


        name = filename.lower()



        # 研究报告优先判断
        if (
            "报告" in name
            or
            "report" in name
            or
            "research" in name
            or
            "趋势" in name
            or
            "分析" in name
            or
            "调研" in name
        ):

            return "研究报告"



        # 买家访谈
        if (
            "ur-b" in name
            or
            "buyer" in name
            or
            "访谈" in name
            or
            "interview" in name
        ):

            return "买家访谈"



        # 供应商访谈
        if (
            "ur-s" in name
            or
            "supplier" in name
            or
            "vendor" in name
        ):

            return "供应商访谈"



        return "其他"


file_classifier = FileClassifier()



########################################################
# Context Extractor
########################################################

class ContextExtractor:


    def extract(
        self,
        text: str,
        query: str,
        window: int = 400
    ):


        if not text:

            return (
                "",
                "",
                ""
            )


        lower_text = text.lower()


        positions = []


        for keyword in [
            query
        ]:

            pos = lower_text.find(
                keyword.lower()
            )

            if pos >= 0:

                positions.append(pos)



        # Try expanded keywords

        if not positions:

            for token in tokenize(query):

                pos = lower_text.find(
                    token.lower()
                )

                if pos >= 0:

                    positions.append(pos)

                    break



        if not positions:

            return (
                text[:window],
                "",
                text[window:window*2]
            )



        pos = positions[0]


        start = max(
            0,
            pos - window
        )


        end = min(
            len(text),
            pos + window
        )


        before = text[start:pos].strip()


        match = text[
            pos:
            min(
                len(text),
                pos + len(query) + 200
            )
        ].strip()


        after = text[
            pos + len(query):
            end
        ].strip()



        return (
            before,
            match,
            after
        )



context_extractor = ContextExtractor()



########################################################
# Duplicate Remover
########################################################

class DuplicateRemover:


    def remove(
        self,
        results: List[SearchResult]
    ):


        seen = set()


        output = []


        for r in results:


            key = (
                r.file,
                r.snippet[:100]
            )


            if key in seen:

                continue


            seen.add(key)

            output.append(r)



        return output



duplicate_remover = DuplicateRemover()



########################################################
# Result Builder
########################################################

class ResultBuilder:


    def build(
        self,
        file_obj: dict,
        score: float,
        query: str
    ) -> SearchResult:


        filename = file_obj.get(
            "file",
            ""
        )


        content = file_obj.get(
            "content",
            ""
        )


        title = file_obj.get(
            "title",
            ""
        )


        category = file_classifier.classify(
            filename
        )


        before, match, after = (
            context_extractor.extract(
                content,
                query
            )
        )



        return SearchResult(

            file=filename,

            title=title,

            category=category,

            score=score,

            snippet=match,

            context_before=before,

            context_after=after,

            github_url=file_obj.get(
                "github_url",
                ""
            ),

            char_count=file_obj.get(
                "char_count",
                len(content)
            )

        )



result_builder = ResultBuilder()
########################################################
# Knowledge Search Core
########################################################

class KnowledgeSearcher:


    def __init__(self):

        self.loader = BundleLoader()

        self.expander = query_expander

        self.ranker = ranking_engine

        self.builder = result_builder



    def load_documents(
        self,
        refresh=False
    ):


        bundle = self.loader.load(
            refresh=refresh
        )


        documents = []


        # Support different bundle structures

        if isinstance(bundle, list):

            documents = bundle


        elif isinstance(bundle, dict):

            if "documents" in bundle:

                documents = bundle["documents"]


            elif "files" in bundle:

                documents = bundle["files"]


            elif "items" in bundle:

                documents = bundle["items"]


            else:

                # fallback

                for key, value in bundle.items():

                    if isinstance(value, list):

                        documents.extend(value)



        logger.info(
            f"Loaded documents: {len(documents)}"
        )


        return documents



    def search(
        self,
        query: str,
        top_k: int = 10,
        refresh: bool = False
    ):


        documents = self.load_documents(
            refresh
        )


        expanded_queries = (
            self.expander.expand(
                query
            )
        )


        logger.info(
            "Expanded query:"
        )

        logger.info(
            expanded_queries
        )


        candidates = []



        for doc in documents:


            content = doc.get(
                "content",
                ""
            )


            title = doc.get(
                "title",
                ""
            )


            filename = doc.get(
                "file",
                ""
            )


            if not content:

                continue



            score = (
                self.ranker.calculate(
                    query=query,
                    expanded_queries=expanded_queries,
                    text=content,
                    title=title,
                    category=file_classifier.classify(
                        filename
                    )
                )
            )



            if score <= 0:

                continue



            result = (
                self.builder.build(
                    doc,
                    score,
                    query
                )
            )


            candidates.append(
                result
            )



        # Sort by score

        candidates.sort(
            key=lambda x:x.score,
            reverse=True
        )



        # Remove duplicates

        candidates = (
            duplicate_remover.remove(
                candidates
            )
        )


        return (
            candidates[:top_k],
            expanded_queries
        )



knowledge_searcher = KnowledgeSearcher()



########################################################
# JSON Formatter
########################################################

def result_to_dict(
    result: SearchResult
):


    return {

        "file":
            result.file,

        "title":
            result.title,

        "category":
            result.category,

        "score":
            result.score,

        "snippet":
            result.snippet,

        "context_before":
            result.context_before,

        "context_after":
            result.context_after,

        "github_url":
            result.github_url,

        "char_count":
            result.char_count

    }



def output_json(
    query,
    results,
    expanded_queries
):


    output = {


        "query":
            query,


        "expanded_queries":
            expanded_queries,


        "results":[]


    }



    for item in results:


        doc = item.get(
            "document",
            {}
        )


        result = {


            "title":
                doc.get(
                    "title",
                    ""
                ),


            "source":
                doc.get(
                    "source",
                    ""
                ),


            "category":
                doc.get(
                    "category",
                    ""
                ),


            "scenario":
                doc.get(
                    "scenario",
                    []
                ),


            "persona":
                doc.get(
                    "persona",
                    ""
                ),


            "evidence":
                item.get(
                    "snippet",
                    ""
                ),


            "score":
                item.get(
                    "score",
                    0
                )

        }


        output["results"].append(
            result
        )



    return output


########################################################
# Pretty Output
########################################################

def print_results(
    data
):


    print("\n")

    print("=" * 80)

    print(
        f"Query: {data['query']}"
    )

    print(
        "Expanded:"
    )

    print(
        ", ".join(
            data["expanded_queries"]
        )
    )


    print("=" * 80)


    for index, item in enumerate(
        data["results"],
        start=1
    ):


        print("\n")

        print(
            f"[{index}] "
            f"{item['title'] or item['file']}"
        )


        print(
            f"Category: "
            f"{item['category']}"
        )


        print(
            f"Score: "
            f"{item['score']}"
        )


        print(
            "\nSnippet:"
        )


        print(
            item["snippet"][:500]
        )


        print(
            "\nGitHub:"
        )


        print(
            item["github_url"]
        )


        print(
            "-" * 80
        )



########################################################
# Main
########################################################

def main():


    parser = build_parser()


    args = parser.parse_args()



    try:


        results, expanded = (
            knowledge_searcher.search(

                query=args.query,

                top_k=args.top,

                refresh=args.refresh

            )
        )


        data = output_json(

            query=args.query,

            results=results,

            expanded_queries=expanded

        )



        if args.json:


            print(

                json.dumps(

                    data,

                    ensure_ascii=False,

                    indent=2

                )

            )


        else:

            print_results(
                data
            )



    except Exception as e:


        logger.exception(
            "Search failed"
        )


        print(
            {
                "error":
                str(e)
            }
        )


        sys.exit(1)



if __name__ == "__main__":

    main()