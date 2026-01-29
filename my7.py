# ===================================================================
# 1. 导入所有需要的库 (无变化)
# ===================================================================
import sys
import os
import io
import traceback
import glob

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QMessageBox, QListWidget, QProgressBar, QSlider)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

import fitz
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import numpy as np
import cv2

# ===================================================================
# 2. 您的核心图像处理函数 (【重大修改】)
# ===================================================================
# 【修改】函数签名，增加三个锐化参数
def deal_image2(image, contrast, sharpen_radius, sharpen_percent, sharpen_threshold):
    imnp = np.array(image)

    if len(imnp.shape) > 2 and imnp.shape[2] == 3:
        gray = cv2.cvtColor(imnp, cv2.COLOR_RGB2GRAY)
    else:
        gray = imnp
    tmp = gray / 8
    kernel = np.array((
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1]
    ))
    mask = cv2.filter2D(tmp,-1, kernel)
    mask = mask.astype(np.uint8)
 
    mask[mask <240] = 0
    mask[mask != 0] = 255
    mask[mask == 0] = 25
    mask[mask == 255] = 0
    mask[mask == 25] = 255

    stretched_image = ImageOps.autocontrast(image,cutoff=1)
    enh_con = ImageEnhance.Contrast(stretched_image)
    img_contrasted = enh_con.enhance(contrast)

    ced = np.array(img_contrasted, dtype=np.uint8)

    if len(imnp.shape) > 2 and imnp.shape[2] == 3:
        result = (~mask)[..., np.newaxis] + (ced & mask[..., np.newaxis])
    else:
        result =  ~mask + (ced & mask)
    image = Image.fromarray(result)

    #image.save("3.png")
    
    # 【修改】图像锐化，使用传入的参数而不是固定值
    img_sharpened = image.filter(ImageFilter.UnsharpMask(
        radius=sharpen_radius, 
        percent=sharpen_percent,
        threshold=sharpen_threshold
    ))
   
    return img_sharpened

# ===================================================================
# 3. 后台处理线程 (【修改】)
# ===================================================================
class Worker(QObject):
    total_progress = pyqtSignal(int, int)
    current_file_progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    # 【修改】构造函数，增加三个锐化参数
    def __init__(self, file_list, contrast_value, radius, percent, threshold):
        super().__init__()
        self.file_list = file_list
        self.contrast = contrast_value
        # 【新增】保存锐化参数
        self.radius = radius
        self.percent = percent
        self.threshold = threshold

    def process_files(self):
        total_files = len(self.file_list)
        processed_files = 0

        try:
            for i, file_path in enumerate(self.file_list):
                self.total_progress.emit(i + 1, total_files)
                output_path = file_path.replace('.pdf', '_enhanced.pdf')
                
                if file_path == output_path:
                    self.current_file_progress.emit(f"跳过已处理文件: {os.path.basename(file_path)}")
                    continue
                
                self.current_file_progress.emit(f"开始处理: {os.path.basename(file_path)}")
                
                with fitz.open(file_path) as doc:
                    page_count = doc.page_count
                    if page_count < 1:
                        continue

                    for page_num, page in enumerate(doc):
                        self.current_file_progress.emit(f"处理 {os.path.basename(file_path)} - 第 {page_num + 1}/{page_count} 页")
                        
                        image_list = page.get_images(full=True)
                        if not image_list:
                            continue
                        
                        for img_info in image_list:
                            xref = img_info[0]
                            base_image = doc.extract_image(xref)
                            if not base_image:
                                continue
                            
                            image_bytes = base_image["image"]
                            image = Image.open(io.BytesIO(image_bytes))
                            
                            # 【修改】调用deal_image2时，传入所有参数
                            processed_image = deal_image2(
                                image, 
                                self.contrast,
                                self.radius,
                                self.percent,
                                self.threshold
                            )

                            buffer = io.BytesIO()
                            dpi = (base_image.get('xres', 96), base_image.get('yres', 96))
                            processed_image.save(buffer, format="PNG", dpi=dpi)
                            
                            page.replace_image(xref, stream=buffer.getvalue())

                        page.clean_contents()
                    
                    doc.save(output_path, garbage=4, deflate=True, clean=True)
                processed_files += 1

            self.finished.emit(f'批量处理完成！\n成功处理了 {processed_files}/{total_files} 个文件。')

        except Exception as e:
            detailed_error = f"处理失败: {e}\n\n详细信息:\n{traceback.format_exc()}"
            self.error.emit(detailed_error)

# ===================================================================
# 4. 主窗口 GUI 类 (【重大修改】)
# ===================================================================
class PDFProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_list = []
        self.thread = None
        self.worker = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PDF扫描件批量增强工具 (PyQt5版)')
        self.setGeometry(300, 300, 500, 600) # 【修改】增加窗口高度以容纳新控件
        self.setAcceptDrops(True)

        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)

        info_label = QLabel('将PDF文件或包含PDF的文件夹拖放到下方列表区域', self)
        
        self.file_list_widget = QListWidget(self)
        self.file_list_widget.setStyleSheet("QListWidget { border: 2px dashed #aaa; border-radius: 5px; }")

        # --- 对比度滑块 ---
        self.contrast_label = QLabel('对比度: 2.0', self)
        self.contrast_slider = QSlider(Qt.Horizontal, self)
        self.contrast_slider.setMinimum(10); self.contrast_slider.setMaximum(40); self.contrast_slider.setValue(20)
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(self.contrast_label); contrast_layout.addWidget(self.contrast_slider)

        # --- 【新增】锐化-半径(Radius)滑块 ---
        self.radius_label = QLabel('锐化半径 (Radius): 1.4', self)
        self.radius_slider = QSlider(Qt.Horizontal, self)
        # UnsharpMask的radius通常是0.5到5之间的浮点数。我们用整数0-50代表0.0-5.0
        self.radius_slider.setMinimum(0); self.radius_slider.setMaximum(50); self.radius_slider.setValue(14) # 默认1.4
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(self.radius_label); radius_layout.addWidget(self.radius_slider)

        # --- 【新增】锐化-百分比(Percent)滑块 ---
        self.percent_label = QLabel('锐化程度 (Percent): 100%', self)
        self.percent_slider = QSlider(Qt.Horizontal, self)
        # Percent是整数，范围通常在50到200之间
        self.percent_slider.setMinimum(50); self.percent_slider.setMaximum(200); self.percent_slider.setValue(100) # 默认100
        percent_layout = QHBoxLayout()
        percent_layout.addWidget(self.percent_label); percent_layout.addWidget(self.percent_slider)
        
        # --- 【新增】锐化-阈值(Threshold)滑块 ---
        self.threshold_label = QLabel('锐化阈值 (Threshold): 0', self)
        self.threshold_slider = QSlider(Qt.Horizontal, self)
        # Threshold是整数，范围通常在0到10之间
        self.threshold_slider.setMinimum(0); self.threshold_slider.setMaximum(10); self.threshold_slider.setValue(0) # 默认0
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(self.threshold_label); threshold_layout.addWidget(self.threshold_slider)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)

        self.process_button = QPushButton('开始处理', self)
        self.process_button.setEnabled(False)
        
        self.clear_button = QPushButton('清空列表', self)

        # --- 【修改】布局 ---
        self.layout.addWidget(info_label)
        self.layout.addWidget(self.file_list_widget)
        self.layout.addLayout(contrast_layout) 
        self.layout.addLayout(radius_layout)      # 【新增】
        self.layout.addLayout(percent_layout)     # 【新增】
        self.layout.addLayout(threshold_layout)   # 【新增】
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.process_button)
        self.layout.addWidget(self.clear_button)
        self.setCentralWidget(self.central_widget)

        # --- 【修改】信号与槽连接 ---
        self.process_button.clicked.connect(self.start_processing)
        self.clear_button.clicked.connect(self.clear_list)
        self.contrast_slider.valueChanged.connect(self.update_contrast_label)
        # 【新增】连接新滑块的信号
        self.radius_slider.valueChanged.connect(self.update_radius_label)
        self.percent_slider.valueChanged.connect(self.update_percent_label)
        self.threshold_slider.valueChanged.connect(self.update_threshold_label)
        
        self.statusBar().showMessage('请拖入文件或文件夹')

    # --- 【新增】三个用于更新锐化参数标签的方法 ---
    def update_contrast_label(self, value):
        self.contrast_label.setText(f'对比度: {value / 10.0:.1f}')

    def update_radius_label(self, value):
        self.radius_label.setText(f'锐化半径 (Radius): {value / 10.0:.1f}')

    def update_percent_label(self, value):
        self.percent_label.setText(f'锐化程度 (Percent): {value}%')

    def update_threshold_label(self, value):
        self.threshold_label.setText(f'锐化阈值 (Threshold): {value}')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        new_files_added = False
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    pdf_files = glob.glob(os.path.join(path, '*.pdf'))
                    for pdf_file in pdf_files:
                        if pdf_file not in self.file_list:
                            self.file_list.append(pdf_file)
                            new_files_added = True
                elif path.lower().endswith('.pdf'):
                    if path not in self.file_list:
                        self.file_list.append(path)
                        new_files_added = True
        
        if new_files_added: self.update_file_list_widget()

    def update_file_list_widget(self):
        self.file_list_widget.clear()
        self.file_list_widget.addItems(self.file_list)
        if self.file_list:
            self.process_button.setEnabled(True)
            self.statusBar().showMessage(f'已添加 {len(self.file_list)} 个文件。')
        else:
            self.process_button.setEnabled(False)

    def clear_list(self):
        self.file_list.clear()
        self.update_file_list_widget()
        self.progress_bar.setValue(0)
        self.statusBar().showMessage('列表已清空，请拖入文件或文件夹')

    def start_processing(self):
        if not self.file_list:
            QMessageBox.warning(self, '警告', '文件列表为空，请先添加文件。')
            return

        self.process_button.setEnabled(False); self.clear_button.setEnabled(False); self.progress_bar.setValue(0)

        # 【修改】获取所有滑块的值
        current_contrast = self.contrast_slider.value() / 10.0
        current_radius = self.radius_slider.value() / 10.0 # 因为滑块是整数，要变回浮点数
        current_percent = self.percent_slider.value()
        current_threshold = self.threshold_slider.value()
        
        self.thread = QThread()
        # 【修改】在创建Worker实例时传入所有参数
        self.worker = Worker(
            self.file_list, 
            current_contrast,
            current_radius,
            current_percent,
            current_threshold
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.process_files)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_error)
        self.worker.total_progress.connect(self.update_total_progress)
        self.worker.current_file_progress.connect(lambda msg: self.statusBar().showMessage(msg))
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def update_total_progress(self, current_num, total_num):
        progress_percent = int((current_num / total_num) * 100)
        self.progress_bar.setValue(progress_percent)
        self.progress_bar.setFormat(f'总进度: {current_num}/{total_num}')

    def processing_finished(self, message):
        self.statusBar().showMessage('全部处理完成！')
        QMessageBox.information(self, '成功', message)
        self.reset_ui()

    def processing_error(self, message):
        self.statusBar().showMessage('处理过程中发生错误！')
        QMessageBox.critical(self, '错误', message)
        self.reset_ui()
    
    def reset_ui(self):
        self.process_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.clear_list() 
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

# ===================================================================
# 5. 程序入口 (无变化)
# ===================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = PDFProcessorApp()
    main_win.show()
    sys.exit(app.exec_())