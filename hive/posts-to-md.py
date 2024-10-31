#!/usr/bin/python
# -*- coding: utf-8 -*-

from beem import Hive
from beem.account import Account
import os
import io
import argparse
import requests
import uuid
from urllib.parse import urlparse
import re
from datetime import datetime, timedelta

def download_image(image_url, path):
    try:
        # Fazer o download da imagem
        response = requests.get(image_url)
        if response.status_code == 200:
            # Extrair a extensão do arquivo
            parsed_url = urlparse(image_url)
            _, ext = os.path.splitext(parsed_url.path)

            # Gerar um nome de arquivo único com UUID
            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(path, unique_filename)

            # Salvar a imagem no disco
            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"Imagem baixada e salva como: {file_path}")
            return unique_filename
        else:
            print(f"Erro ao baixar a imagem: {image_url} (Status Code: {response.status_code})")
            return None
    except Exception as e:
        print(f"Erro ao processar a imagem {image_url}: {e}")
        return None

def extract_images_from_markdown(markdown_content):
    # Procurar por imagens no formato ![alt](image_url)
    image_urls = re.findall(r'!\[.*?\]\((.*?)\)', markdown_content)
    return image_urls

def main(author, path, last=False, include_actifit=False, all_posts=False, today=False, platform="hive"):
    # Escolher a blockchain com base na plataforma
    if platform == "hive":
        node_url = "https://api.hive.blog"
    else:  # steemit
        node_url = "https://api.steemit.com"

    # Conectar à blockchain Hive ou Steemit
    hive = Hive(node=node_url)
    account = Account(author, blockchain_instance=hive)
    
    # Data de ontem e hoje
    yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    today_date = datetime.utcnow().date()

    # Obter os posts da conta
    posts = account.get_blog(limit=500)  # Ajuste o limite conforme necessário
    
    if last:
        # Pega o último post apenas
        posts = [posts[0]] if posts else []
    
    # Processar cada post
    for post in posts:
        if post["author"] != author:
            continue
        
        # Verificar se a tag 'actifit' está no post
        if 'actifit' in post.get('json_metadata', {}).get('tags', []):
            if not include_actifit:
                print(f"Post ignorado devido à tag 'actifit': {post['title']}")
                continue
        
        # Usar o campo created diretamente como datetime
        post_date = post["created"].date()
        
        # Condicionais para --all, --today e posts de ontem
        if not all_posts:
            if today:
                if post_date != today_date:
                    continue
            else:
                if post_date != yesterday:
                    continue
        
        markdown_content = post['body']
        title = post['title']
        permlink = post['permlink']
        link_for_post = f'https://{platform}.blog/@{author}/{permlink}'
        
        # Baixar imagens e substituir os links no markdown
        images = post.get('json_metadata', {}).get('image', [])
        
        if images:
            print(f"Imagens encontradas no post (json_metadata): {images}")
        
        # Extrair imagens do markdown
        markdown_images = extract_images_from_markdown(markdown_content)
        
        if markdown_images:
            print(f"Imagens encontradas no markdown: {markdown_images}")

        # Baixar todas as imagens encontradas no json_metadata e no markdown
        all_images = images + markdown_images
        for image_url in all_images:
            downloaded_image_name = download_image(image_url, path)
            if downloaded_image_name:
                markdown_content = markdown_content.replace(image_url, downloaded_image_name)
        
        post_final = f'---\n<br />**Postado originalmente na rede {platform.capitalize()}: [{link_for_post}]({link_for_post})** <br />\n----'
        yaml_prefix = '---\n'
        TitleYaml = title.replace(':', '').replace('\'', '').replace('#', '').replace('(', '').replace(')', '')
        
        # Construir o prefixo YAML
        yaml_prefix += f'title: {TitleYaml}\n'
        yaml_prefix += f'date: {post["created"]}\n'
        yaml_prefix += f'permlink: /{platform}/{permlink}\n'
        yaml_prefix += 'type: posts\n'
        yaml_prefix += f'categories: ["{platform.capitalize()}"]\n'
        yaml_prefix += f'author: {author}\n---\n'
        
        # Nome do arquivo
        filename = os.path.join(path, f"{post_date}_{permlink}.md")
       
        # Salvar o conteúdo em um arquivo Markdown
        with io.open(filename, "w", encoding="utf-8") as f:
            f.write(yaml_prefix + markdown_content + post_final)
        
        print(f"Post salvo: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("author", help="Nome da conta na Hive ou Steemit")
    parser.add_argument("path", help="Caminho onde os arquivos Markdown serão salvos")
    parser.add_argument("--last", action="store_true", help="Pega o último post somente")
    parser.add_argument("--actifit", action="store_true", help="Inclui posts com a tag 'actifit'")
    parser.add_argument("--all", action="store_true", help="Pega todos os posts, ignorando o filtro de data")
    parser.add_argument("--today", action="store_true", help="Pega apenas os posts de hoje")
    parser.add_argument("--steemit", action="store_true", help="Usar a rede Steemit em vez da Hive")
    
    args = parser.parse_args()
    
    # Definir a plataforma (Hive ou Steemit)
    platform = "steemit" if args.steemit else "hive"
    
    main(args.author, args.path, args.last, args.actifit, args.all, args.today, platform)

