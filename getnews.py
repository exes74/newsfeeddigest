#!/opt/readwise/venv/bin/python

import requests
import datetime
import urllib3
from getpass import getpass
import pprint
from bs4 import BeautifulSoup
from openai import OpenAI
import openai
import re
import datetime
import smtplib
import re
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from notion_client import Client
import os
import json
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_PATH = "/etc/scrt/api_key"

def load_api_keys(config_path):
	try:
		with open(config_path, "r") as file:
			data = json.load(file)
		return data
	except FileNotFoundError:
		print(f"Erreur : Le fichier {config_path} n'existe pas.")
		return None
	except json.JSONDecodeError:
		print("Erreur : Le fichier JSON est mal formaté.")
		return None
# Charger les clés
api_keys = load_api_keys(CONFIG_PATH)
# Vérifier et assigner les variables si le fichier a été bien chargé
if api_keys:
	READWISE_API_TOKEN = api_keys.get("READWISE_API_TOKEN")
	NOTION_DATABASE_ID = api_keys.get("NOTION_DATABASE_ID")	
	OPENAI_API_KEY = api_keys.get("OPENAI_API_KEY")
	NOTION_TOKEN = api_keys.get("NOTION_TOKEN")
	SENDER_MAIL = api_keys.get("SENDER_MAIL")
	RECIPIENT_MAIL = api_keys.get("RECIPIENT_MAIL")
	RECIPIENT_MAIL_SECU = api_keys.get("RECIPIENT_MAIL_SECU")
	PWD_MAIL = api_keys.get("PWD_MAIL")
	# Affichage de test (retirer en prod)
	print("Clés chargées avec succès !")

BASE_URL = 'https://readwise.io/api/v2'
notion = Client(auth=NOTION_TOKEN)
ASSISTANT_ID = "asst_8XTJeyIuPctQM5AKm8VrBGb8"

def load_api_keys(config_path):
	"""
	Load API keys from a JSON configuration file.
	"""
	try:
		with open(config_path, "r") as file:
			data = json.load(file)
		return data
	except FileNotFoundError:
		print(f"Erreur : Le fichier {config_path} n'existe pas.")
		return None
	except json.JSONDecodeError:
		print("Erreur : Le fichier JSON est mal formaté.")
		return None



def push_to_notion(site_name, published_date, tag, title_without_tag, content_without_title, url):
	"""
	Stores an article in the specified Notion database.
	"""
	database_info = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
	print(database_info)
	
	"""
	Enregistre un article dans la base Notion spécifiée par NOTION_DATABASE_ID.
	"""	 
	new_page_properties = {
		# Titre : 
		"Title": {
			"title": [
				{
					"text": {
						"content": title_without_tag
					}
				}
			]
		},
		"Tag": {
			"multi_select": [
				{
					"name": tag
				}
			]
		},
		"Source": {
			"rich_text": [
				{
					"text": {
						"content": site_name
					}
				}
			]
		},
		"Publication Date": {
			"date": {
				"start": published_date
			}
		},
		"Summary": {
			"rich_text": [
				{
					"text": {
						"content": content_without_title
					}
				}
			]
		},
		"Article URL": {
			"url": url
		}
	}

	try:
		response = notion.pages.create(
			parent={"database_id": NOTION_DATABASE_ID},
			properties=new_page_properties
		)
		print(f"Article '{title_without_tag}' inséré dans Notion avec succès. ID : {response['id']}")
	except Exception as e:
		print(f"Erreur lors de l'insertion de l'article '{title_without_tag}' dans Notion : {e}")



def convert_html_to_text(html_content):
	"""
	Converts HTML content into plain text by removing tags.
	"""
	soup = BeautifulSoup(html_content, 'html.parser')
	text = soup.get_text()
	cleaned_text = ' '.join(text.split())
	return cleaned_text

def fetch_reader_document_list_api(updated_after=None):
	"""
	Fetch articles from Readwise API with optional filtering by date.
	"""
	full_data = []
	next_page_cursor = None
	while True:
		params = {}
		if next_page_cursor:
			params['pageCursor'] = next_page_cursor
		if updated_after:
			params['updatedAfter'] = updated_after
		params['category'] = 'rss'
		params['withHtmlContent']=True
		# print("Making export api request with params " + str(params) + "...")
		response = requests.get(
			url="https://readwise.io/api/v3/list/",
			params=params,
			headers={"Authorization": f"Token {READWISE_API_TOKEN}"}, verify=False
		)
		full_data.extend(response.json()['results'])
		next_page_cursor = response.json().get('nextPageCursor')
		if not next_page_cursor:
			break
	# return full_data
	return full_data[:20]

# def summarize_gpt(article_content, retries=5, delay=2):
	# attempt = 0
	# """
	# Summarizes an article using OpenAI's GPT model.
	# """
	# while attempt < retries:
		# try:
			# client = openai.OpenAI(api_key=OPENAI_API_KEY)

			# Création d'un thread pour interagir avec l'assistant
			# thread = client.beta.threads.create()

			# Envoi de l'article à l'Assistant
			# message = client.beta.threads.messages.create(
				# thread_id=thread.id,
				# role="user",
				# content=article_content
				# )

			# Lancer l'Assistant sur le thread
			# run = client.beta.threads.runs.create(
						# thread_id=thread.id,
						# assistant_id=ASSISTANT_ID
				# )

			# Attendre que l'Assistant ait fini de traiter la requête
			# while run.status not in ["completed", "failed"]:
				# run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

			# Récupérer la réponse finale de l'Assistant
			# messages = client.beta.threads.messages.list(thread_id=thread.id)
			# response_content = messages.data[0].content[0].text.value  # Récupération du texte de la réponse
			# try:
				# data = json.loads(response_content)
				# tag = data.get("tag", "")
				# title_without_tag = data.get("title", "")
				# content_without_title = data.get("summary", "")
			# except json.JSONDecodeError as e:
				# tag = "ERROR"
				# title_without_tag = "ERROR"
				# content_without_title = "ERROR"
			
			# if title_without_tag != "ERROR":
				# return response_content
			# else:
				# raise ValueError("GPT returned ERROR code")
				# attempt += 1
				# print (str(attempt))

		# except Exception as e:
				# print(f"Erreur lors de l'appel à l'API : {e}")
				# return None
	# return None
import openai
import json
import time

def summarize_gpt(article_content, retries=5, delay=2):
	attempt = 0

	client = openai.OpenAI(api_key=OPENAI_API_KEY)

	while attempt < retries:
		try:
			thread = client.beta.threads.create()

			client.beta.threads.messages.create(
				thread_id=thread.id,
				role="user",
				content=article_content
			)

			run = client.beta.threads.runs.create(
				thread_id=thread.id,
				assistant_id=ASSISTANT_ID
			)

			while True:
				run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

				if run.status == "completed":
					break
				elif run.status == "failed":
					print(f"Erreur API : {run.last_error}")
					raise Exception(run.last_error)
				
				time.sleep(1)

			messages = client.beta.threads.messages.list(thread_id=thread.id)
			response_content = messages.data[0].content[0].text.value

			# Affichage du contenu brut pour identifier l'erreur
			print("\n--- Réponse brute renvoyée par GPT ---\n")
			print(response_content)
			print("\n-------------------------------------\n")

			# Essai de parsing
			try:
				data = json.loads(response_content)
				return response_content
			except json.JSONDecodeError as e:
				print(f"Erreur de parsing JSON : {e}")
				attempt += 1
				time.sleep(delay)
				print(f"Tentative {attempt}/{retries}")

		except Exception as e:
			print(f"Erreur lors de l'appel à l'API : {e}")
			attempt += 1
			time.sleep(delay)
			print(f"Tentative {attempt}/{retries}")

	print("Échec après toutes les tentatives.")
	return None

def send_html_email(to_email, subject, html_body):
	"""
	Sends an HTML email with the specified subject and body.
	"""
	from_email = SENDER_MAIL
	password = PWD_MAIL	 #

	msg = MIMEMultipart("alternative")
	msg["Subject"] = subject
	msg["From"] = from_email
	msg["To"] = to_email

	text_body = "Votre client mail ne supporte pas l'affichage HTML."
	part_text = MIMEText(text_body, "plain", "utf-8")
	msg.attach(part_text)
	part_html = MIMEText(html_body, "html", "utf-8")
	msg.attach(part_html)
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
		server.login(from_email, password)
		server.sendmail(from_email, to_email, msg.as_string())
	# print("E-mail HTML envoyé avec succès !")


def main():
	"""
	Main function to fetch, process, summarize, store, and email articles.
	"""
	yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
	docs_after_date = datetime.datetime.now() - datetime.timedelta(hours=48)	
	articles = fetch_reader_document_list_api(docs_after_date.isoformat())	
	if articles:
		articles_by_tag = {}
		for article in articles:
			if article['published_date'] != yesterday_str:
				continue
			print('-----------------------------------------------------------------------------------')
			print('Traitement de l\'article: '+article['title'])
			content = convert_html_to_text(article['html_content'])
			print('Contenu: '+content)
			summary = summarize_gpt(content)

			try:
				data = json.loads(summary)
				tag = data.get("tag", "")
				title_without_tag = data.get("title", "")
				content_without_title = data.get("summary", "")
			except json.JSONDecodeError as e:
				tag = "ERROR"
				title_without_tag = "ERROR"
				content_without_title = "ERROR"

			article_data = {
				'source': article['site_name'],
				'published_date': article['published_date'],
				'tag': tag,
				'title': title_without_tag,
				'summary': content_without_title,
				'url' : article['source_url']
			}
			push_to_notion(
				site_name=article['site_name'],
				published_date=article['published_date'],
				tag=tag,
				title_without_tag=title_without_tag,
				content_without_title=content_without_title,
				url=article['source_url']
			)
			if tag not in articles_by_tag:
				articles_by_tag[tag] = []
			articles_by_tag[tag].append(article_data)
			
		#EMAIL YCA
		email_body = []
		email_body.append("<h2>Récapitulatif des articles de la veille</h2><br>")

		for current_tag, articles_list in articles_by_tag.items():
			if current_tag:
				email_body.append(f"<br><br><h3>=== Thématique : {current_tag} ===</h3><br>")
			else:
				email_body.append("<br><br><h3>=== Thématique : Sans tag ===</h3><br>")

			for art in articles_list:
				source_link = f'<a href="{art["url"]}">{art["source"]}</a>'
				email_body.append(f"""
					<h4>{art['title']}</h4>					
					<p>{art['summary']}</p>
					<p><strong> {art['published_date']} / {source_link}</strong></p>
					<hr/>
				""")
		email_body_str = "\n".join(email_body)
		subject = f"Récapitulatif des articles du {docs_after_date.strftime('%Y-%m-%d')}"
		send_html_email(
			to_email=RECIPIENT_MAIL,
			subject=subject,
			html_body=email_body_str
		)

		email_body = []
		email_body.append("<h2>Récapitulatif des articles Cyber de la veille</h2><br>")

		for current_tag, articles_list in articles_by_tag.items():
			if current_tag == 'Cybersecurite':
				email_body.append(f"<br><br><h3>=== Thématique : {current_tag} ===</h3><br>")

				for art in articles_list:
					source_link = f'<a href="{art["url"]}">{art["source"]}</a>'
					email_body.append(f"""
						<h4>{art['title']}</h4>					
						<p>{art['summary']}</p>
						<p><strong> {art['published_date']} / {source_link}</strong></p>
						<hr/>
					""")
		email_body_str = "\n".join(email_body)
		subject = f"Récapitulatif des articles du {docs_after_date.strftime('%Y-%m-%d')}"
		send_html_email(
			to_email=RECIPIENT_MAIL_SECU,
			subject=subject,
			html_body=email_body_str
		)
	else:
		email_body_str = "Aucun article trouvé pour les dernières 24h."
		subject = f"Récapitulatif des articles du {docs_after_date.strftime('%Y-%m-%d')}"
		send_html_email(
			to_email=RECIPIENT_MAIL,
			subject=subject,
			html_body=email_body_str
		)
		print("Aucun article trouvé pour les dernières 24h.")

if __name__ == '__main__':
	main()
