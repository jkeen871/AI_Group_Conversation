import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from sklearn.decomposition import PCA


class VectorGraphVisualizer(QWidget):
    def __init__(self, rag):
        super().__init__()
        self.rag = rag
        self.figure = Figure(figsize=(5, 4), dpi=100)  # Start with a smaller default size
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.ax = self.figure.add_subplot(111)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.setMinimumSize(200, 150)  # Set a minimum size for the widget

    def reset(self):
        self.ax.clear()
        self.ax.set_title("Word Vector Space (PCA)")
        self.ax.set_xlabel("First Principal Component")
        self.ax.set_ylabel("Second Principal Component")
        self.canvas.draw()
        self.logger.info("Vector graph reset")

    def set_rag(self, rag):
        self.rag = rag
        self.update_plot()

    def update_plot(self):
        try:
            self.ax.clear()
            if self.rag.vector_history is not None and len(self.rag.word_history) > 0:
                vectors = self.rag.vector_history.toarray()
                if vectors.shape[0] > 1:
                    pca = PCA(n_components=2)
                    points = pca.fit_transform(vectors)
                    self.ax.scatter(points[:, 0], points[:, 1], alpha=0.7)

                    # Plot a subset of words to avoid cluttering
                    plot_indices = np.linspace(0, len(self.rag.word_history) - 1, 50, dtype=int)
                    for i in plot_indices:
                        self.ax.annotate(self.rag.word_history[i], (points[i, 0], points[i, 1]),
                                         xytext=(5, 5), textcoords='offset points',
                                         fontsize=8, alpha=0.8)

                    self.ax.set_title("Word Vector Space (PCA)")
                    self.ax.set_xlabel("First Principal Component")
                    self.ax.set_ylabel("Second Principal Component")
                elif vectors.shape[0] == 1:
                    self.ax.scatter([vectors[0, 0]], [0])
                    self.ax.annotate(self.rag.word_history[0], (vectors[0, 0], 0),
                                     xytext=(5, 5), textcoords='offset points',
                                     fontsize=8)
                    self.ax.set_title("Single Word Vector")
                else:
                    self.logger.warning("No vectors to plot")
            else:
                self.logger.warning("Vector history is None or empty, unable to update plot")
                self.ax.set_title("No data to display")

            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            self.logger.error(f"Error updating plot: {e}")

    def resizeEvent(self, event):
        try:
            super().resizeEvent(event)
            new_size = event.size()
            self.logger.debug(f"New size - Width: {new_size.width()}, Height: {new_size.height()}")

            # Ensure minimum dimensions
            width = max(new_size.width(), 200)
            height = max(new_size.height(), 150)

            if width > 0 and height > 0:
                winch = width / self.figure.dpi
                hinch = height / self.figure.dpi
                self.logger.debug(f"Calculated size in inches - Width: {winch}, Height: {hinch}")

                self.figure.set_size_inches(winch, hinch, forward=False)
                self.figure.tight_layout()
                self.canvas.draw()
            else:
                self.logger.warning(f"Invalid widget size - Width: {width}, Height: {height}")
        except Exception as e:
            self.logger.error(f"Error in resizeEvent: {e}")

    def closeEvent(self, event):
        try:
            self.figure.clf()
            super().closeEvent(event)
        except Exception as e:
            self.logger.error(f"Error in closeEvent: {e}")
