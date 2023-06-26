from aiogram import types


text_create_giveaway = 'Создать розыгрыш'
text_cancel = 'Отмена'
text_all_giveaways = 'Все ГИВы'

cancel = types.KeyboardButton(text=text_cancel)
create_giveaway = types.KeyboardButton(text=text_create_giveaway)
all_giveaways = types.KeyboardButton(text=text_all_giveaways)
