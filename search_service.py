#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
search_service.py

Knowledge Base Search API

Purpose:
Expose search_kb_v2.py as an API service

Future compatible:
- GPT Actions
- Custom GPT
- MCP Server
- AI Agent

"""

from flask import Flask
from flask import request
from flask import jsonify

from search_kb_v2 import knowledge_searcher
from search_kb_v2 import output_json


##################################################
# Flask App
##################################################

app = Flask(__name__)



##################################################
# Health Check
##################################################

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({

        "status":
            "ok",

        "service":
            "UX Research Knowledge Search API",

        "version":
            "1.0"

    })



##################################################
# Search API
##################################################

@app.route(
    "/search",
    methods=["POST"]
)
def search():


    data = request.get_json()


    if not data:

        return jsonify({

            "error":
                "JSON body required"

        }),400



    query = data.get(
        "query"
    )


    top_k = data.get(
        "top_k",
        5
    )


    refresh = data.get(
        "refresh",
        False
    )



    if not query:

        return jsonify({

            "error":
                "query required"

        }),400



    results, expanded = (

        knowledge_searcher.search(

            query=query,

            top_k=top_k,

            refresh=refresh

        )

    )



    response = output_json(

        query=query,

        results=results,

        expanded_queries=expanded

    )


    return jsonify(response)




##################################################
# Start
##################################################

if __name__ == "__main__":


    app.run(

        host="0.0.0.0",

        port=8000,

        debug=False

    )