import logging
import requests
from transformers import AutoTokenizer


class GPT:
    def __init__(self):
        self.system_content = " "
        self.URL = 'http://localhost:1234/v1/chat/completions'
        self.HEADERS = {"Content-Type": "application/json"}
        self.MAX_TOKENS_IN_QUEST = 2048
        self.TEMPERATURE = 0.9
        self.MAX_TOKENS_IN_ANS = 30

    def make_prompt(self, user_content, gpt_answer, system_prompt):
        tokens_in_quest = self.count_tokens(user_content)  # подсчет токенов
        if tokens_in_quest > self.MAX_TOKENS_IN_QUEST:
            gpt_answer = ""
            return False, "Текст слишком большой! Пожалуйста, переформулируйте Ваш вопрос.", gpt_answer

        if user_content.lower() == "продолжи!":
            assistant_content = " " + gpt_answer  # вносим историю ответов нейросети
            task = " "

        else:
            task = user_content
            gpt_answer = ""
            assistant_content = " "
        try:
            resp = requests.post(
                url=self.URL,
                headers=self.HEADERS,
                # тело запроса
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": task},
                        {"role": "assistant", "content": assistant_content}
                    ],
                    "temperature": self.TEMPERATURE,
                    "max_tokens": self.MAX_TOKENS_IN_ANS,
                }
            )
        except requests.exceptions.ConnectionError:
            logging.critical("подключение к нейросети отсутствует")
            gpt_answer = ""
            return False, ("Ну всё, я забыл язык нейросетей и не могу к ним подключиться."
                           " Пожалуйста, зайдите чуть позже."), gpt_answer

        # Печатаем ответ
        if resp.status_code == 200 and 'choices' in resp.json():
            result = resp.json()['choices'][0]['message']['content']

            if result == "":
                gpt_answer = ""
                return False,  ("Ответ окончен.\n\n"
                                "Жду Ваши вопросы!"), gpt_answer

            gpt_answer += result
            return True, gpt_answer, result
        else:
            gpt_answer = ""
            return False, ("Не удалось получить ответ от нейросети.\n"
                           f"Текст ошибки: {resp.json()}"), gpt_answer

    @staticmethod
    def count_tokens(prompt):
        tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")  # название модели
        return len(tokenizer.encode(prompt))
