from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class Slack:
  def __init__(self, token: str = None, channel: str = None):
    self.token = token
    self.channel = channel

    if not self.token:
      raise ValueError(
        "Slack Bot Token is required. "
        "Set SLACK_BOT_TOKEN in .env or pass it as an argument."
      )

    self.client = WebClient(token=self.token)

  def post_message(self, text: str):
    if self.channel is None:
      raise ValueError("Channel ID is required to post a message.")

    try:
      response = self.client.chat_postMessage(
        channel=self.channel,
        text=text
      )
      print(f"Message posted successfully: {response['ts']}")
    except SlackApiError as e:
      print(f"Error posting message: {e.response['error']}")
