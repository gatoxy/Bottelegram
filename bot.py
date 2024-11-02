import telebot
import requests
from bs4 import BeautifulSoup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json

BOT_TOKEN = '6744916639:AAGywcPkGFQ-uQBv2gWdVNqCkFjfaPyI-MQ'
bot = telebot.TeleBot(BOT_TOKEN)

anime_links = {}

# Definindo o cabeçalho com User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
}

@bot.message_handler(commands=['p'])
def search_anime(message):
    anime_name = message.text[len('/p '):].strip().lower()
    if anime_name:
        search_url = f'https://animefire.plus/pesquisar/{anime_name.replace(" ", "%20")}'
        response = requests.get(search_url, headers=headers)  # Incluindo headers aqui
        soup = BeautifulSoup(response.content, 'html.parser')

        animes = soup.find_all('article', class_='cardUltimosEps')

        if animes:
            markup = InlineKeyboardMarkup()
            for index, anime in enumerate(animes):
                title = anime.find('h3', class_='animeTitle').text.strip()
                link = anime.find('a')['href']
                full_link = link if link.startswith('http') else f'https://animefire.plus{link}'

                anime_links[f"anime_{index}"] = full_link
                markup.add(InlineKeyboardButton(text=title, callback_data=f"anime_{index}"))

            bot.send_message(message.chat.id, "Animes encontrados:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Nenhum anime encontrado com esse nome.")
    else:
        bot.send_message(message.chat.id, "Por favor, forneça o nome do anime. Exemplo: /p boruto")

@bot.callback_query_handler(func=lambda call: call.data.startswith('anime_'))
def anime_details(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

    anime_id = call.data
    if anime_id in anime_links:
        anime_url = anime_links[anime_id]
        
        response = requests.get(anime_url, headers=headers)  # Incluindo headers aqui
        soup = BeautifulSoup(response.content, 'html.parser')

        title = soup.find('h1', class_='quicksand400').text.strip()

        synopsis_tag = soup.find('div', class_='divSinopse')
        if synopsis_tag:
            synopsis = synopsis_tag.find('span', class_='spanAnimeInfo')
            if synopsis:
                synopsis_text = synopsis.text.strip()
            else:
                synopsis_text = "Sinopse não disponível"
        else:
            synopsis_text = "Sinopse não disponível"
        
        truncated_synopsis = synopsis_text[:250] + '...' if len(synopsis_text) > 250 else synopsis_text

        image_tag = soup.find('div', class_='sub_animepage_img').find('img')
        image_url = image_tag['data-src'] if image_tag else None

        episode_id = f"episodes_{anime_id.split('_')[1]}" 
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="Episódios", callback_data=episode_id))

        bot.send_photo(
            call.message.chat.id,
            photo=image_url,
            caption=f"**{title}**\n\n{truncated_synopsis}",
            parse_mode='Markdown',
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('episodes_'))
def show_episodes(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

    anime_index = call.data.split('_')[1]
    anime_id = f'anime_{anime_index}'
    
    if anime_id in anime_links:
        anime_url = anime_links[anime_id]
        
        response = requests.get(anime_url, headers=headers)  # Incluindo headers aqui
        soup = BeautifulSoup(response.content, 'html.parser')

        episodes_section = soup.find('section', class_='mt-3 mb-2')
        if episodes_section:
            episode_links = episodes_section.find_all('a', class_='lEp') 
            if episode_links:
                for episode in episode_links:
                    episode_title = episode.text.strip()
                    episode_url = episode['href']
                    full_episode_link = episode_url if episode_url.startswith('http') else f'https://animefire.plus{episode_url}'
                    
                    episode_response = requests.get(full_episode_link, headers=headers)  # Incluindo headers aqui
                    episode_soup = BeautifulSoup(episode_response.content, 'html.parser')
                    
                    video_tag = episode_soup.find('video')
                    if video_tag and 'data-video-src' in video_tag.attrs:
                        video_src = video_tag['data-video-src']
                        
                        video_response = requests.get(video_src, headers=headers)  # Incluindo headers aqui
                        video_data = json.loads(video_response.text)

                        message_text = f"**{episode_title}**\n\n"
                        if 'data' in video_data:
                            for video in video_data['data']:
                                message_text += f"{video['label']}: {video['src']}\n"
                        else:
                            message_text += "Não foi possível obter as informações do vídeo."

                        bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
                    else:
                        bot.send_message(call.message.chat.id, f"Não foi possível encontrar o vídeo para {episode_title}.")

            else:
                bot.send_message(call.message.chat.id, "Nenhum episódio disponível.")
        else:
            bot.send_message(call.message.chat.id, "Não foi possível encontrar a lista de episódios.")
    else:
        bot.send_message(call.message.chat.id, "Anime não encontrado.")

bot.polling()
