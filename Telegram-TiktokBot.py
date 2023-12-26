import re
import json
import requests
import pycountry
from decouple import config
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

class Users:
    URI_BASE = 'https://www.tiktok.com/'

    def __init__(self):
        self.user = ''
        self.status_code = ''

    def details(self, user):
        if not user:
            raise ValueError('Missing required argument: "user"')

        self.user = self.prepare(user)

        request_data = self.request()
        response = self.extract(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"([^>]+)>([^<]+)<\/script>',
            request_data
        )

        validate_props = response['__DEFAULT_SCOPE__']['webapp.user-detail']

        if 'userInfo' not in validate_props:
            self.status_code = 404

        if self.status_code:
            return self.template(
                validate_props,
                'userInfo',
                self.status_code,
                {
                    'user': {
                        'id': 'id',
                        'username': 'nickname',
                        'profileName': 'uniqueId',
                        'avatar': 'avatarMedium',
                        'description': 'signature',
                        'region': 'region',
                        'verified': 'verified',
                    },
                    'stats': {
                        'following': 'followingCount',
                        'follower': 'followerCount',
                        'video': 'videoCount',
                        'like': 'heartCount',
                    },
                }
            )

    def request(self, method='GET', get_params=None):
        if get_params is None:
            get_params = {}

        headers = {'user-agent': 'Mozilla/5.0 (compatible; Google-Apps-Script)'}
        url = f'{self.URI_BASE}@{self.user}/?lang=ru'

        response = requests.get(url, headers=headers)

        self.status_code = response.status_code

        return response.text

    def prepare(self, user):
        return re.sub(r'@', '', user, 1).lower()

    def extract(self, pattern, data):
        matches = re.search(pattern, data)
        if matches:
            return json.loads(matches.group(2))

    def template(self, request_, request_module, status_code_, template_=None):
        if template_ is None:
            template_ = {}

        result = {'code': status_code_}

        if status_code_ == 200:
            for user_info_key, value in template_.items():
                result[user_info_key] = {}  # Initialize the nested dictionary
                for key, values in value.items():
                    if key == 'region':
                        region_value = request_[request_module][user_info_key][values]
                        country_code = region_value  # İlk iki karakteri al
                        flag_emoji = self.get_flag_emoji(country_code)
                        result[user_info_key][key] = f"{region_value} - {flag_emoji}"
                    else:
                        result[user_info_key][key] = request_[request_module][user_info_key][values]
        elif status_code_ == 404:
            result['error'] = 'This account cannot be found.'
        else:
            result['error'] = 'The page cannot load.'

        formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
        return formatted_result

    def get_flag_emoji(self, country_code):
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            flag_emoji = country.flag
            country_name = country.name
            return (f"{country_name} - {flag_emoji}")
            #return pycountry.countries.get(alpha_2=country_code).flag and name
        else:
            return '🌐'  # Default: dünya bayrağı


def get_tiktok_details(update: Update, context: CallbackContext) -> None:
    username = update.message.text
    user_instance = Users()
    result = user_instance.details(username)
    update.message.reply_text(result, parse_mode='HTML')


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    BOT_TOKEN = config('BOT_TOKEN')
    updater = Updater(token=BOT_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, get_tiktok_details))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
