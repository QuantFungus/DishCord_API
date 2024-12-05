
# DishCord API - Bite by Byte

  

### Rensselaer Center for Open Source Software

### Fall 2024 (September - December '24)

### [Link](https://discord.gg/tdvc6Mjh8f) to the Discord Server

### [Link](https://drive.google.com/file/d/1bk7ust5zL6JCJlzqYRZkay1Mtw6YMngX/view?usp=sharing) to poster

### Members:

- Isaih Bernardo - bernai@rpi.edu - 4 credits

- William Lin - linw10@rpi.edu - 4 credits

### Overview and Goals:

- Discord bot one would chat with to suggest meals to cook

- Users can set their initial preferred flavors, favorite dishes, and dietary restrictions

- After the initial setup, users provide ingredients they have and the bot generates a recipe around those ingredients

- Users could specify if they want a quick 15 minute dish or to meal prep for later

- Users can also specify if they're trying to lose or gain weight

- Meals provided are tagged with difficulty, flavors, and time

- Detailed nutritional breakdowns provide information like calories and macros

- Recipes can be favorited and referenced at a later time
  
### Tech:

- Pycord - API wrapper we’ll use to write the bot

- ChatGPT API - To write out endless personalized recipes

- We already have experience with using LLM APIs, but intend to learn more about the use of hosting chatbots

### Milestones:

- Learn basics of Pycord and create simple back and forth messages (By end of September)

- Make sure we can host the bot at appropriate times and have a working GPT token (Also by end of September)

- Have a barebones working bot, doesn't have to include user preferences and other features mentioned above (Mid October)

- Make sure there's some way to store user preferences and favorite dishes, along with as many of the mentioned features as possible (November)

- Have some sort of hosting for the bot to continue to be used by anyone and not just in dev time (End of semester)

One major blocker is that hosting a bot outside of dev time requires a host, so either an old computer, a raspberry pi, or some paid service. We'll have to figure that out when we get there.

Also, ChatGPT API keys give a limit to the amount of tokens per month. That's another hurdle to conquer when we get there. Maybe we can use an alternative LLM API or just continue paying for more tokens.