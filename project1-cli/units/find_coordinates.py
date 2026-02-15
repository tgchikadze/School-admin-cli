"""Помощник для определения координат на PDF-шаблоне"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Создаём PDF с сеткой координат
c = canvas.Canvas("coordinate_grid.pdf", pagesize=A4)
width, height = A4

# Рисуем сетку с шагом 50 пунктов
c.setFont("Helvetica", 6)

for x in range(0, int(width), 50):
    c.line(x, 0, x, height)
    c.drawString(x + 2, 10, str(x))

for y in range(0, int(height), 50):
    c.line(0, y, width, y)
    c.drawString(10, y + 2, str(y))

c.setFont("Helvetica", 8)
c.drawString(width/2 - 50, height - 30, "Сетка координат для PDF (0,0 = нижний левый угол)")

c.save()
print("✅ Создан файл coordinate_grid.pdf")
print("Откройте его вместе с вашим бланком, чтобы определить координаты полей")
