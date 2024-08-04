import pyperclip
from qtpy.QtCore import Qt
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy

from pyqt_openai import DEFAULT_ICON_SIZE, ICON_FAVORITE_NO, ICON_INFO, ICON_COPY, ICON_FAVORITE_YES
from pyqt_openai.gpt_widget.responseInfoDialog import ResponseInfoDialog
from pyqt_openai.gpt_widget.messageTextBrowser import MessageTextBrowser
from pyqt_openai.models import ChatMessageContainer
from pyqt_openai.pyqt_openai_data import DB
from pyqt_openai.widgets.button import Button
from pyqt_openai.widgets.circleProfileImage import RoundedImage


class AIChatUnit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__initVal()
        self.__initUi()

    def __initVal(self):
        self.__lbl = ''
        self.__result_info = ''
        app = QApplication.instance()
        self.__show_markdown = app.show_as_markdown

    def __initUi(self):
        menuWidget = QWidget()
        lay = QHBoxLayout()

        self.__icon = RoundedImage()
        self.__icon.setMaximumSize(*DEFAULT_ICON_SIZE)

        self.__favoriteBtn = Button()
        self.__favoriteBtn.setStyleAndIcon(ICON_FAVORITE_NO)
        self.__favoriteBtn.setCheckable(True)
        self.__favoriteBtn.toggled.connect(self.__favorite)

        self.__infoBtn = Button()
        self.__infoBtn.setStyleAndIcon(ICON_INFO)
        self.__infoBtn.clicked.connect(self.__showResponseInfoDialog)

        self.__copyBtn = Button()
        self.__copyBtn.setStyleAndIcon(ICON_COPY)
        self.__copyBtn.clicked.connect(self.__copy)

        lay.addWidget(self.__icon)
        lay.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.MinimumExpanding))
        lay.addWidget(self.__favoriteBtn)
        lay.addWidget(self.__infoBtn)
        lay.addWidget(self.__copyBtn)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(1)

        menuWidget.setLayout(lay)
        menuWidget.setMaximumHeight(menuWidget.sizeHint().height())

        lay = QVBoxLayout()
        self.__mainWidget = QWidget()
        self.__mainWidget.setLayout(lay)

        lay = QVBoxLayout()
        lay.addWidget(menuWidget)
        lay.addWidget(self.__mainWidget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.setLayout(lay)

        self.setBackgroundRole(QPalette.ColorRole.AlternateBase)
        self.setAutoFillBackground(True)

    def __copy(self):
        pyperclip.copy(self.getText())

    def __favorite(self, f, insert_f=True):
        favorite = 1 if f else 0
        if favorite:
            self.__favoriteBtn.setStyleAndIcon(ICON_FAVORITE_YES)
        else:
            self.__favoriteBtn.setStyleAndIcon(ICON_FAVORITE_NO)
        if insert_f:
            current_date = DB.updateMessage(self.__result_info.id, favorite)
            self.__result_info.favorite = favorite
            self.__result_info.favorite_set_date = current_date

    def __showResponseInfoDialog(self):
        dialog = ResponseInfoDialog(self.__result_info, parent=self)
        dialog.exec()

    def setAlignment(self, a0):
        lay = self.__mainWidget.layout()
        for i in range(lay.count()):
            if lay.itemAt(i) and lay.itemAt(i).widget():
                widget = lay.itemAt(i).widget()
                if isinstance(widget, MessageTextBrowser):
                    widget.setAlignment(a0)

    def toggleGUI(self, f: bool):
        self.__favoriteBtn.setEnabled(f)
        self.__copyBtn.setEnabled(f)
        self.__infoBtn.setEnabled(f)

    def __setResponseInfo(self, arg: ChatMessageContainer):
        self.__result_info = arg
        self.__favorite(True if arg.favorite else False, insert_f=False)

    def getResponseInfo(self):
        """
        Get the response information
        :return: ChatMessageContainer

        Note: This function is used to get the response information after the response is generated.
        """
        try:
            if self.__result_info and isinstance(self.__result_info, ChatMessageContainer):
                return self.__result_info
            else:
                raise AttributeError('Response information is not available')
        except AttributeError as e:
            raise e

    def afterResponse(self, arg: ChatMessageContainer):
        self.toggleGUI(True)
        self.__setResponseInfo(arg)
        if isinstance(self.__lbl, MessageTextBrowser):
            if arg.is_json_response_available:
                self.__lbl.setJson(arg.content)
            else:
                if self.__show_markdown:
                    self.__lbl.setMarkdown(arg.content)
                else:
                    self.__lbl.setText(arg.content)
            self.__lbl.adjustBrowserHeight()

    def setText(self, text: str):
        self.__lbl = MessageTextBrowser()
        if self.__show_markdown:
            self.__lbl.setMarkdown(text)
        else:
            self.__lbl.setText(text)

        self.__lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.__lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.__lbl.setOpenExternalLinks(True)

        self.__mainWidget.layout().addWidget(self.__lbl)
        self.__lbl.adjustBrowserHeight()

    def addText(self, text: str):
        unit = self.__mainWidget.layout().itemAt(self.__mainWidget.layout().count()-1).widget()
        if isinstance(unit, MessageTextBrowser):
            unit.setText(unit.toPlainText()+text)
            unit.adjustBrowserHeight()

    def getIcon(self):
        return self.__icon.getImage()

    def setIcon(self, filename):
        self.__icon.setImage(filename)

    def getText(self):
        return self.__lbl.toPlainText()

    def getLbl(self):
        return self.__lbl