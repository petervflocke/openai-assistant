import json
import os
import sys
import webbrowser

from qtpy.QtCore import Qt, QSettings
from qtpy.QtWidgets import QHBoxLayout, QWidget, QSizePolicy, QVBoxLayout, QSplitter, \
    QFileDialog, QMessageBox, QPushButton

from pyqt_openai import THREAD_TABLE_NAME, INI_FILE_NAME, JSON_FILE_EXT_LIST_STR, ICON_SIDEBAR, ICON_SETTING, \
    ICON_PROMPT, \
    FILE_NAME_LENGTH, MAXIMUM_MESSAGES_IN_PARAMETER, DEFAULT_SHORTCUT_FIND, DEFAULT_SHORTCUT_LEFT_SIDEBAR_WINDOW, \
    DEFAULT_SHORTCUT_CONTROL_PROMPT_WINDOW, DEFAULT_SHORTCUT_RIGHT_SIDEBAR_WINDOW, QFILEDIALOG_DEFAULT_DIRECTORY
from pyqt_openai.gpt_widget.chatNavWidget import ChatNavWidget
from pyqt_openai.gpt_widget.chatWidget import ChatWidget
from pyqt_openai.gpt_widget.prompt import Prompt
from pyqt_openai.gpt_widget.prompt_gen_widget.promptGeneratorWidget import PromptGeneratorWidget
from pyqt_openai.gpt_widget.right_sidebar.aiPlaygroundWidget import AIPlaygroundWidget
from pyqt_openai.lang.translations import LangClass
from pyqt_openai.models import ChatThreadContainer, ChatMessageContainer
from pyqt_openai.openAiThread import OpenAIThread, LlamaOpenAIThread
from pyqt_openai.pyqt_openai_data import DB, get_argument, LLAMAINDEX_WRAPPER
from pyqt_openai.util.script import open_directory, get_generic_ext_out_of_qt_ext, message_list_to_txt, \
    conv_unit_to_html, \
    add_file_to_zip, getSeparator
from pyqt_openai.widgets.button import Button
from pyqt_openai.widgets.notifier import NotifierWidget


class OpenAIChatBotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__initVal()
        self.__initUi()

    def __initVal(self):
        self.__settings_ini = QSettings(INI_FILE_NAME, QSettings.Format.IniFormat)
        self.__notify_finish = self.__settings_ini.value('notify_finish', type=bool)

        if not self.__settings_ini.contains('show_chat_list'):
            self.__settings_ini.setValue('show_chat_list', True)
        if not self.__settings_ini.contains('show_setting'):
            self.__settings_ini.setValue('show_setting', True)
        if not self.__settings_ini.contains('show_prompt'):
            self.__settings_ini.setValue('show_prompt', True)

        self.__show_chat_list = self.__settings_ini.value('show_chat_list', type=bool)
        self.__show_setting = self.__settings_ini.value('show_setting', type=bool)
        self.__show_prompt = self.__settings_ini.value('show_prompt', type=bool)

        self.__maximum_messages_in_parameter = self.__settings_ini.value('maximum_messages_in_parameter', MAXIMUM_MESSAGES_IN_PARAMETER, type=int)

        self.__is_showing_favorite = False

    def __initUi(self):
        self.__chatNavWidget = ChatNavWidget(ChatThreadContainer.get_keys(), THREAD_TABLE_NAME)
        self.__chatWidget = ChatWidget()
        self.__browser = self.__chatWidget.getChatBrowser()

        self.__prompt = Prompt()
        self.__prompt.onStoppedClicked.connect(self.__stopResponse)

        self.__lineEdit = self.__prompt.getMainPromptInput()
        self.__aiPlaygroundWidget = AIPlaygroundWidget()

        self.__aiPlaygroundWidget.onToggleJSON.connect(self.__prompt.toggleJSON)

        try:
            self.__aiPlaygroundWidget.onDirectorySelected.connect(LLAMAINDEX_WRAPPER.set_directory)
        except Exception as e:
            QMessageBox.critical(self, LangClass.TRANSLATIONS["Error"], str(e))

        self.__promptGeneratorWidget = PromptGeneratorWidget()

        self.__sideBarBtn = Button()
        self.__sideBarBtn.setStyleAndIcon(ICON_SIDEBAR)
        self.__sideBarBtn.setCheckable(True)
        self.__sideBarBtn.setToolTip(LangClass.TRANSLATIONS['Chat List'] + f' ({DEFAULT_SHORTCUT_LEFT_SIDEBAR_WINDOW})')
        self.__sideBarBtn.setChecked(self.__show_chat_list)
        self.__sideBarBtn.toggled.connect(self.__toggle_sidebar)
        self.__sideBarBtn.setShortcut(DEFAULT_SHORTCUT_LEFT_SIDEBAR_WINDOW)

        self.__settingBtn = Button()
        self.__settingBtn.setStyleAndIcon(ICON_SETTING)
        self.__settingBtn.setToolTip(LangClass.TRANSLATIONS['Chat Settings'] + f' ({DEFAULT_SHORTCUT_RIGHT_SIDEBAR_WINDOW})')
        self.__settingBtn.setCheckable(True)
        self.__settingBtn.setChecked(self.__show_setting)
        self.__settingBtn.toggled.connect(self.__toggle_setting)
        self.__settingBtn.setShortcut(DEFAULT_SHORTCUT_RIGHT_SIDEBAR_WINDOW)

        self.__promptBtn = Button()
        self.__promptBtn.setStyleAndIcon(ICON_PROMPT)
        self.__promptBtn.setToolTip(LangClass.TRANSLATIONS['Prompt Generator'] + f' ({DEFAULT_SHORTCUT_CONTROL_PROMPT_WINDOW})')
        self.__promptBtn.setCheckable(True)
        self.__promptBtn.setChecked(self.__show_prompt)
        self.__promptBtn.toggled.connect(self.__toggle_prompt)
        self.__promptBtn.setShortcut(DEFAULT_SHORTCUT_CONTROL_PROMPT_WINDOW)

        sep = getSeparator('vertical')

        toggleFindToolButton = QPushButton(LangClass.TRANSLATIONS['Show Find Tool'])
        toggleFindToolButton.setCheckable(True)
        toggleFindToolButton.setChecked(True)
        toggleFindToolButton.toggled.connect(self.__chatWidget.toggleMenuWidget)
        toggleFindToolButton.setShortcut(DEFAULT_SHORTCUT_FIND)

        lay = QHBoxLayout()
        lay.addWidget(self.__sideBarBtn)
        lay.addWidget(self.__settingBtn)
        lay.addWidget(self.__promptBtn)
        lay.addWidget(sep)
        lay.addWidget(toggleFindToolButton)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.__menuWidget = QWidget()
        self.__menuWidget.setLayout(lay)
        self.__menuWidget.setMaximumHeight(self.__menuWidget.sizeHint().height())

        sep = getSeparator('horizontal')

        self.__chatNavWidget.added.connect(self.__addThread)
        self.__chatNavWidget.clicked.connect(self.__showChat)
        self.__chatNavWidget.cleared.connect(self.__clearChat)
        self.__chatNavWidget.onImport.connect(self.__importChat)
        self.__chatNavWidget.onExport.connect(self.__exportChat)
        self.__chatNavWidget.onFavoriteClicked.connect(self.__showFavorite)

        self.__lineEdit.returnPressed.connect(self.__chat)

        lay = QHBoxLayout()
        lay.addWidget(self.__prompt)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        self.__queryWidget = QWidget()
        self.__queryWidget.setLayout(lay)
        self.__queryWidget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        lay = QVBoxLayout()
        lay.addWidget(self.__chatWidget)
        lay.addWidget(self.__queryWidget)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        chatWidget = QWidget()
        chatWidget.setLayout(lay)

        self.__rightSideBar = QSplitter()
        self.__rightSideBar.setOrientation(Qt.Orientation.Vertical)
        self.__rightSideBar.addWidget(self.__aiPlaygroundWidget)
        self.__rightSideBar.addWidget(self.__promptGeneratorWidget)
        self.__rightSideBar.setSizes([450, 550])
        self.__rightSideBar.setChildrenCollapsible(False)
        self.__rightSideBar.setHandleWidth(2)
        self.__rightSideBar.setStyleSheet(
            '''
            QSplitter::handle:vertical
            {
                background: #CCC;
                height: 1px;
            }
            ''')


        mainWidget = QSplitter()
        mainWidget.addWidget(self.__chatNavWidget)
        mainWidget.addWidget(chatWidget)
        mainWidget.addWidget(self.__rightSideBar)
        mainWidget.setSizes([100, 500, 400])
        mainWidget.setChildrenCollapsible(False)
        mainWidget.setHandleWidth(2)
        mainWidget.setStyleSheet(
        '''
        QSplitter::handle:horizontal
        {
            background: #CCC;
            height: 1px;
        }
        ''')

        lay = QVBoxLayout()
        lay.addWidget(self.__menuWidget)
        lay.addWidget(sep)
        lay.addWidget(mainWidget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.setLayout(lay)

        self.__lineEdit.setFocus()

        # Put this below to prevent the widgets pop up when app is opened
        self.__chatNavWidget.setVisible(self.__show_chat_list)
        self.__aiPlaygroundWidget.setVisible(self.__show_setting)
        self.__promptGeneratorWidget.setVisible(self.__show_prompt)

    def __toggle_sidebar(self, x):
        self.__chatNavWidget.setVisible(x)
        self.__show_chat_list = x
        self.__settings_ini.setValue('show_chat_list', x)

    def __toggle_setting(self, x):
        self.__aiPlaygroundWidget.setVisible(x)
        self.__show_setting = x
        self.__settings_ini.setValue('show_setting', x)

    def __toggle_prompt(self, x):
        self.__promptGeneratorWidget.setVisible(x)
        self.__show_prompt = x
        self.__settings_ini.setValue('show_prompt', x)

    def showThreadToolWidget(self, f):
        self.__chatWidget.toggleMenuWidget(f)

    def showSecondaryToolBar(self, f):
        self.__menuWidget.setVisible(f)

    def toolTipLinkClicked(self, url):
        webbrowser.open(url)

    def setAIEnabled(self, f):
        self.__lineEdit.setEnabled(f)

    def refreshCustomizedInformation(self):
        self.__chatWidget.refreshCustomizedInformation()

    def __chat(self):
        try:
            # Get necessary parameters
            stream = self.__settings_ini.value('stream', type=bool)
            model = self.__settings_ini.value('model', type=str)
            system = self.__settings_ini.value('system', type=str)
            temperature = self.__settings_ini.value('temperature', type=float)
            max_tokens = self.__settings_ini.value('max_tokens', type=int)
            top_p = self.__settings_ini.value('top_p', type=float)
            is_json_response_available = 1 if self.__settings_ini.value('json_object', type=bool) else 0
            frequency_penalty = self.__settings_ini.value('frequency_penalty', type=float)
            presence_penalty = self.__settings_ini.value('presence_penalty', type=float)
            use_llama_index = self.__settings_ini.value('use_llama_index', type=bool)

            # Get image files
            images = self.__prompt.getImageBuffers()

            messages = self.__browser.getMessages(self.__maximum_messages_in_parameter)

            cur_text = self.__prompt.getContent()

            json_content = self.__prompt.getJSONContent()

            is_llama_available = False
            if use_llama_index:
                # Check llamaindex is available
                is_llama_available = LLAMAINDEX_WRAPPER.get_directory() != ''
                if is_llama_available:
                    if LLAMAINDEX_WRAPPER.is_query_engine_set():
                        pass
                    else:
                        LLAMAINDEX_WRAPPER.set_query_engine(streaming=stream, similarity_top_k=3)
                else:
                    QMessageBox.warning(self, LangClass.TRANSLATIONS["Warning"], LangClass.TRANSLATIONS['LLAMA index is not available. Please check the directory path or disable the llama index.'])
                    return

            use_max_tokens = self.__settings_ini.value('use_max_tokens', type=bool)

            # Check JSON response is valid
            if is_json_response_available:
                if not json_content:
                    QMessageBox.critical(self, LangClass.TRANSLATIONS["Error"], LangClass.TRANSLATIONS['JSON content is empty. Please fill in the JSON content field.'])
                    return
                try:
                    json.loads(json_content)
                except Exception as e:
                    QMessageBox.critical(self, LangClass.TRANSLATIONS["Error"], f'{LangClass.TRANSLATIONS["JSON content is not valid. Please check the JSON content field."]}\n\n{e}')
                    return

            # Get parameters for OpenAI
            openai_param = get_argument(model, system, messages, cur_text, temperature, top_p, frequency_penalty, presence_penalty, stream,
                                      use_max_tokens, max_tokens,
                                      images,
                                      is_llama_available, is_json_response_available, json_content)

            # If there is no current conversation selected on the list to the left, make a new one.
            if self.__chatWidget.isNew():
                self.__addThread()

            # Additional information of user's input
            additional_info = {
                'role': 'user',
                'content': cur_text,
                'model_name': openai_param['model'],
                'finish_reason': '',
                'prompt_tokens': '',
                'completion_tokens': '',
                'total_tokens': '',

                'is_json_response_available': is_json_response_available,
            }

            container_param = {k: v for k, v in {**openai_param, **additional_info}.items() if k in ChatMessageContainer.get_keys()}

            # Create a container for the user's input and output from the chatbot
            container = ChatMessageContainer(**container_param)

            query_text = self.__prompt.getContent()
            self.__browser.showLabel(query_text, False, container)

            # Run a different thread based on whether the llama-index is enabled or not.
            if is_llama_available:
                self.__t = LlamaOpenAIThread(LLAMAINDEX_WRAPPER, openai_arg=openai_param, query_text=query_text, info=container)
            else:
                self.__t = OpenAIThread(openai_param, info=container)
            self.__t.started.connect(self.__beforeGenerated)
            self.__t.replyGenerated.connect(self.__browser.showLabel)
            self.__t.streamFinished.connect(self.__browser.streamFinished)
            self.__t.start()
            self.__t.finished.connect(self.__afterGenerated)

            # Remove image files widget from the window
            self.__prompt.resetUploadImageFileWidget()
        except Exception as e:
            # get the line of error and filename
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            QMessageBox.critical(self, LangClass.TRANSLATIONS["Error"], f'''
            {str(e)},
            'File: {filename}',
            'Line: {lineno}'
            ''')

    def __stopResponse(self):
        self.__t.stop_streaming()

    def __toggleWidgetWhileChatting(self, f):
        self.__lineEdit.setExecuteEnabled(f)
        self.__chatNavWidget.setEnabled(f)
        self.__prompt.showWidgetInPromptDuringResponse(not f)

    def __beforeGenerated(self):
        self.__toggleWidgetWhileChatting(False)
        self.__lineEdit.clear()

    def __afterGenerated(self):
        self.__toggleWidgetWhileChatting(True)
        self.__lineEdit.setFocus()
        if not self.isVisible():
            if self.__notify_finish:
                self.__notifierWidget = NotifierWidget(informative_text=LangClass.TRANSLATIONS['Response 👌'], detailed_text = self.__browser.getLastResponse())
                self.__notifierWidget.show()
                self.__notifierWidget.doubleClicked.connect(self.window().show)

    def __showChat(self, id, title):
        self.__showFavorite(False)
        self.__chatNavWidget.activateFavoriteFromParent(False)
        conv_data = DB.selectCertainThreadMessages(id)
        self.__chatWidget.showTitle(title)
        self.__browser.replaceThread(conv_data, id)
        self.__prompt.showWidgetInPromptDuringResponse(False)

    def __clearChat(self):
        self.__chatWidget.showTitle('')
        self.__browser.resetChatWidget(0)
        self.__prompt.showWidgetInPromptDuringResponse(False)

    def __addThread(self):
        title = LangClass.TRANSLATIONS['New Chat']
        cur_id = DB.insertThread(title)
        self.__browser.resetChatWidget(cur_id)
        self.__chatWidget.showTitle(title)
        self.__browser.replaceThread(DB.selectCertainThreadMessages(cur_id), cur_id)
        self.__lineEdit.setFocus()
        self.__chatNavWidget.add(called_from_parent=True)

    def __importChat(self, data):
        try:
            # Import thread
            for thread in data:
                cur_id = DB.insertThread(thread['name'], thread['insert_dt'], thread['update_dt'])
                messages = thread['messages']
                # Import message
                for message in messages:
                    message['thread_id'] = cur_id
                    container = ChatMessageContainer(**message)
                    DB.insertMessage(container)
            self.__chatNavWidget.refreshData()
        except Exception as e:
            QMessageBox.critical(self, LangClass.TRANSLATIONS["Error"], LangClass.TRANSLATIONS['Check whether the file is a valid JSON file for importing.'])

    def __exportChat(self, ids):
        file_data = QFileDialog.getSaveFileName(self, LangClass.TRANSLATIONS['Save'], QFILEDIALOG_DEFAULT_DIRECTORY, f'{JSON_FILE_EXT_LIST_STR};;txt files Compressed File (*.zip);;html files Compressed File (*.zip)')
        if file_data[0]:
            filename = file_data[0]
            ext = os.path.splitext(filename)[-1] or get_generic_ext_out_of_qt_ext(file_data[1])
            if ext == '.zip':
                compressed_file_type = file_data[1].split(' ')[0].lower()
                ext_dict = {'txt': {'ext':'.txt', 'func':message_list_to_txt}, 'html': {'ext': '.html', 'func':conv_unit_to_html}}
                for id in ids:
                    row_info = DB.selectThread(id)
                    # Limit the title length to file name length
                    title = row_info['name'][:FILE_NAME_LENGTH]
                    txt_filename = f'{title}_{id}{ext_dict[compressed_file_type]["ext"]}'
                    txt_content = ext_dict[compressed_file_type]['func'](DB, id, title)
                    add_file_to_zip(txt_content, txt_filename, os.path.splitext(filename)[0] + '.zip')
            elif ext == '.json':
                DB.export(ids, filename)
            open_directory(os.path.dirname(filename))

    def setColumns(self, columns):
        self.__chatNavWidget.setColumns(columns)

    def __showFavorite(self, f):
        if f:
            lst = DB.selectFavorite()
            if len(lst) == 0:
                return
            else:
                lst = [ChatMessageContainer(**dict(c)) for c in lst]
                self.__browser.replaceThreadForFavorite(lst)
        self.__prompt.setEnabled(not f)
        self.__is_showing_favorite = f