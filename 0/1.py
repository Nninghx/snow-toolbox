import tkinter as tk
from tkinter import messagebox, filedialog
import webbrowser
import csv


def generate_links():
	input_text = entry.get()
	numbers = [num.strip() for num in input_text.split(',') if num.strip().isdigit()]
	if not numbers:
		messagebox.showerror('错误', '请输入有效的数字，多个用逗号分隔')
		return
	show_links(numbers)

def show_links(numbers):
	for widget in link_frame.winfo_children():
		widget.destroy()
	global current_links
	current_links = []
	for num in numbers:
		url = f'https://mall.bilibili.com/neul-next/detailuniversal/detail.html?page=detailuniversal_detail&itemsId={num}'
		link = tk.Label(link_frame, text=url, fg='blue', cursor='hand2', font=('Arial', 12, 'underline'))
		link.pack(anchor='w', pady=2)
		# 使用默认参数绑定，避免lambda闭包问题
		link.bind('<Button-1>', lambda e, url=url: webbrowser.open(url))
		current_links.append((num, url))



def export_csv():
	if not current_links:
		messagebox.showerror('导出失败', '没有可导出的链接')
		return
	file_path = filedialog.asksaveasfilename(title='导出CSV', defaultextension='.csv', filetypes=[('CSV文件', '*.csv')])
	if not file_path:
		return
	try:
		with open(file_path, 'w', encoding='utf-8', newline='') as f:
			writer = csv.writer(f)
			writer.writerow(['uid', 'link'])
			for uid, link in current_links:
				writer.writerow([uid, link])
		messagebox.showinfo('导出成功', f'已导出到 {file_path}')
	except Exception as e:
		messagebox.showerror('导出失败', str(e))



root = tk.Tk()
root.title('B站空间链接生成器')
root.geometry('600x400')
try:
	root.iconbitmap('Image/icon.ico')
except Exception as e:
	print(f'设置图标失败: {e}')

# 说明文档内容
desc = (
	'功能说明：\n'
	'- 输入B站UID（可批量，逗号分隔），点击“生成链接”自动生成跳转链接。\n'
	'- 点击链接可直接在浏览器打开对应空间。\n'
	'- 支持将所有生成的链接导出为CSV表格。\n'
	'- 作者:宁幻雪'
)
tk.Label(root, text=desc, font=('Arial', 11), justify='left', anchor='w', fg='#444').pack(fill='x', padx=20, pady=(10,0))

tk.Label(root, text='请输入B站空间UID（可批量，逗号分隔）：', font=('Arial', 12)).pack(pady=10)
entry = tk.Entry(root, font=('Arial', 12), width=50)
entry.pack(pady=5)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)

tk.Button(btn_frame, text='生成链接', font=('Arial', 12), command=generate_links).pack(side='left', padx=5)
tk.Button(btn_frame, text='导出CSV', font=('Arial', 12), command=export_csv).pack(side='left', padx=5)

link_frame = tk.Frame(root)
link_frame.pack(fill='both', expand=True, padx=20, pady=10)

current_links = []

root.mainloop()
