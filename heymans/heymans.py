import logging
import jinja2
from . import config, library
from .documentation import Documentation, FAISSDocumentationSource
from .messages import Messages
from .model import model
from .tools import TopicsTool, SearchTool, CodeInterpreterTool
logger = logging.getLogger('heymans')


class Heymans:
    
    def __init__(self, user_id, persistent=False, encryption_key=None):
        self.user_id = user_id
        self.encryption_key = encryption_key
        if isinstance(self.encryption_key, str):
            self.encryption_key = self.encryption_key.encode()
        logger.info(f'user {user_id} with encryption_key {encryption_key}')
        self.documentation = Documentation(
            self, sources=[FAISSDocumentationSource(self)])
        self.search_model = model(self, config.search_model)
        self.answer_model = model(self, config.answer_model)
        self.condense_model = model(self, config.condense_model)
        self.messages = Messages(self, persistent)
        self._tools = {'topics': TopicsTool(self),
                       'search': SearchTool(self),
                       'code_interpreter': CodeInterpreterTool(self)}
    
    def send_user_message(self, message):
        self.messages.append('user', message)
        while True:
            if len(self.documentation) == 0:
                reply = self.search_model.predict(self.messages.prompt())
            else:
                reply = self.answer_model.predict(self.messages.prompt())
                if isinstance(reply, str):
                    logger.info(f'reply: {reply}')
                    break
            if isinstance(reply, dict):
                logger.info(f'tool action: {reply}')
                self._run_tools(message, reply)
            else:
                logger.info(f'expecting tool action but received reply')
            self.documentation.strip_irrelevant(message)
            if 'reply' in reply:
                reply = reply['reply']
                break
        metadata = self.messages.append('assistant', reply)
        self.documentation.clear()
        return reply, metadata

    def _run_tools(self, message, reply):
        if not isinstance(reply, dict):
            logger.warning(f'expecting dict, not {reply}')
            return
        logger.info(f'running tools')
        for key, value in reply.items():
            if key in self._tools:
                self._tools[key].use(message, value)
