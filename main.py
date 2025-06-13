from PyQt5.QtWidgets import QApplication
from ui import AudioPlayer
import sys
if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = AudioPlayer()
    player.show()
    sys.exit(app.exec_())