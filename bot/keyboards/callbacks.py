from aiogram.utils.callback_data import CallbackData


admin = CallbackData('admin', 'cmd')
nav = CallbackData('nav', 'action', 'value')
export = CallbackData('export', 'action', 'value')
winner = CallbackData('winner', 'action', 'value')
cancel = CallbackData('cancel', 'value', sep='|')
add_post = CallbackData('add_post', 'action', 'giveid')
send_post = CallbackData('send_post', 'confirm')
sponsor = CallbackData('sponsor', 'action', 'spid')
add_chat = CallbackData('chat', 'action', 'giveid')
user_voite = CallbackData('voite', 'gived')
