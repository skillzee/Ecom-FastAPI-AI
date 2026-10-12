from pathlib import Path
import re
import shutil
from html import escape

import fitz
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                              TableStyle, PageBreak, Flowable, Preformatted)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/project'
QA = ROOT / 'tmp/project-artifacts/qa'
QA.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts')
for name, file in [('Body', 'arial.ttf'), ('Bold', 'arialbd.ttf'),
                   ('Serif', 'georgia.ttf'), ('Mono', 'consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT / file)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Body', boldItalic='Bold')
INK = colors.HexColor('#24362c')
GREEN = colors.HexColor('#344d3e')
MUTED = colors.HexColor('#667063')
PAPER = colors.HexColor('#faf9f5')
LINE = colors.HexColor('#d8ded2')
styles = {
 'body': ParagraphStyle('body', fontName='Body', fontSize=9.5, leading=14, textColor=INK, spaceAfter=8),
 'h1': ParagraphStyle('h1', fontName='Serif', fontSize=26, leading=31, textColor=INK, spaceAfter=14),
 'h2': ParagraphStyle('h2', fontName='Bold', fontSize=17, leading=23, textColor=GREEN, spaceBefore=4, spaceAfter=12),
 'h3': ParagraphStyle('h3', fontName='Bold', fontSize=11, leading=16, textColor=GREEN, spaceBefore=9, spaceAfter=7),
 'cell': ParagraphStyle('cell', fontName='Body', fontSize=8.4, leading=11.7, textColor=INK),
 'code': ParagraphStyle('code', fontName='Mono', fontSize=8, leading=11, textColor=INK, backColor=colors.HexColor('#edf0e8'), borderPadding=10, spaceAfter=10),
}

def inline(s):
    s = escape(s)
    s = re.sub(r'`([^`]+)`', r'<font name="Mono">\1</font>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s

class Diagram(Flowable):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.width = A4[0] - 100
        self.height = {'architecture': 180, 'entities': 125, 'auth': 100, 'cache': 180}[kind]
    def draw(self):
        c = self.canv
        def box(x,y,w,h,label):
            c.setFillColor(colors.HexColor('#edf0e8')); c.setStrokeColor(LINE)
            c.roundRect(x,y,w,h,5,fill=1,stroke=1)
            c.setFillColor(INK); c.setFont('Body',8.2)
            lines = label.split('\n')
            for i, line in enumerate(lines):
                c.drawCentredString(x+w/2, y+h/2+(len(lines)-1)*5-i*10-3, line)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(GREEN); c.setFillColor(GREEN); c.setLineWidth(.7)
            c.line(x1,y1,x2,y2)
            dx,dy=x2-x1,y2-y1
            if abs(dx)>abs(dy):
                s=1 if dx>0 else -1; p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-s*5,y2+2.5);p.lineTo(x2-s*5,y2-2.5);p.close()
            else:
                s=1 if dy>0 else -1;p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-2.5,y2-s*5);p.lineTo(x2+2.5,y2-s*5);p.close()
            c.drawPath(p,fill=1,stroke=0)
        if self.kind=='architecture':
            box(0,142,150,30,'Browser storefront')
            box(172,142,150,30,'Node /api proxy')
            box(344,142,150,30,'FastAPI + CurrentUser')
            arrow(150,157,172,157);arrow(322,157,344,157)
            box(344,84,150,34,'SQLite\nUsers / books / cart / orders')
            arrow(419,142,419,118)
            box(172,84,150,34,'LangChain agent\nUser-bound tools')
            arrow(344,142,300,118);arrow(322,101,344,101)
            box(0,28,150,35,'Configured chat model\nFAISS + embeddings')
            arrow(172,90,135,63)
            box(172,28,150,35,'Book scraper\nFive-minute memory cache')
            arrow(247,84,247,63)
            c.setStrokeColor(GREEN);c.line(500,157,500,74);c.line(494,157,500,157)
            c.line(500,74,300,74);arrow(300,74,300,63)
            box(344,28,150,35,'Books to Scrape\nFirst listing page')
            arrow(322,45,344,45)
        elif self.kind=='entities':
            box(0,72,125,32,'USERS')
            box(184,72,125,32,'CART_ITEMS')
            box(369,72,125,32,'PRODUCTS')
            arrow(125,88,184,88);arrow(369,88,309,88)
            box(0,12,125,32,'ORDERS')
            box(184,12,125,32,'ORDER_ITEMS')
            arrow(62,72,62,44);arrow(125,28,184,28)
            c.setFont('Body',7.5);c.setFillColor(MUTED)
            c.drawString(328,19,'Order items retain snapshots')
        elif self.kind=='auth':
            labels=['Verify password hash','Issue/store JWT','Bearer request','Validate JWT claims','Find SQLite user']
            for i,label in enumerate(labels):
                x=(i%3)*172; y=58 if i<3 else 8
                box(x,y,150,30,label)
            arrow(150,73,172,73);arrow(322,73,344,73)
            c.setStrokeColor(GREEN);c.line(419,58,419,45);c.line(419,45,75,45);arrow(75,45,75,38)
            arrow(150,23,172,23)
        else:
            box(145,145,205,28,'Read current store product')
            box(145,102,205,28,'External listing cache valid?')
            arrow(247,145,247,130)
            box(0,53,150,30,'Yes: reuse listing')
            box(172,53,150,30,'No: fetch + parse')
            box(344,53,150,30,'Failure: return error')
            arrow(185,102,90,83);arrow(247,102,247,83);arrow(322,68,344,68)
            box(172,9,150,29,'Success: cache for 300s')
            arrow(247,53,247,38)
            box(0,9,150,29,'Match title; INR + GBP')
            arrow(75,53,75,38);arrow(172,23,150,23)

def table(rows):
    columns=len(rows[0]); width=A4[0]-100
    proportions = {2:[.29,.71],3:[.36,.16,.48]}[columns]
    data=[[Paragraph(inline(cell),styles['cell']) for cell in row] for row in rows]
    t=Table(data,colWidths=[width*p for p in proportions],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0e7da')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LINEBELOW',(0,0),(-1,-1),.4,LINE),
    ]))
    return t

def document(source, title):
    lines=source.read_text(encoding='utf-8').splitlines()
    story=[]; i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1;continue
        if line=='<!-- pagebreak -->': story.append(PageBreak());i+=1;continue
        if line.startswith('```'):
            kind=line[3:];i+=1;block=[]
            while i<len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]);i+=1
            if kind=='mermaid': story.append(Diagram(block[0].removeprefix('%% ').strip()))
            else: story.append(Preformatted('\n'.join(block),styles['code']))
            story.append(Spacer(1,8));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',v) for v in row): rows.append(row)
                i+=1
            story.extend([table(rows),Spacer(1,10)]);continue
        level=next((n for n in [3,2,1] if line.startswith('#'*n+' ')),None)
        if level:
            story.append(Paragraph(inline(line[level+1:]),styles['h'+str(level)]));i+=1;continue
        if line.startswith('- ') or re.match(r'^\d+\. ',line):
            prefix='- ' if line.startswith('- ') else re.match(r'^\d+\. ',line).group()
            story.append(Paragraph(inline(line[len(prefix):]),styles['body'],bulletText=prefix.strip()))
            i+=1;continue
        block=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','<!--','- ')):
            block.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(' '.join(block)),styles['body']))
    def page(c,d):
        c.setFillColor(INK);c.setFont('Bold',8);c.drawString(50,A4[1]-32,'EVERYDAY / '+title.upper())
        c.setStrokeColor(LINE);c.line(50,42,A4[0]-50,42)
        c.setFont('Body',8);c.setFillColor(MUTED)
        c.drawString(50,28,'12 October 2026');c.drawRightString(A4[0]-50,28,str(d.page))
    pdf=OUT/(source.stem+'.pdf')
    SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=50,leftMargin=50,
                      topMargin=56,bottomMargin=56,title=title,author='Everyday project').build(story,onFirstPage=page,onLaterPages=page)

def poster():
    w,h=A3
    c=canvas.Canvas(str(OUT/'Everyday-Poster.pdf'),pagesize=A3)
    c.setTitle('Everyday - Book storefront introduction')
    c.setFillColor(PAPER);c.rect(0,0,w,h,fill=1,stroke=0)
    c.setFillColor(INK);c.setFont('Serif',76);c.drawString(54,h-106,'everyday')
    c.setFont('Body',12);c.setFillColor(MUTED);c.drawRightString(w-54,h-91,'BOOK STOREFRONT')
    c.setFillColor(GREEN);c.setFont('Serif',35);c.drawString(54,h-164,'Your next book, a little closer.')
    c.setFont('Body',14);c.setFillColor(MUTED)
    c.drawString(54,h-195,'Browse books. Ask for help. Compare prices. Keep your orders together.')
    image=OUT/'Everyday-Books-Illustration.png'
    c.drawImage(str(image),(w-675)/2,510,width=675,height=450,mask='auto')
    features=[
       ('01  Browse the collection','Search by title, sort by price and filter for books in stock.'),
       ('02  Compare book prices','Check Everyday against Books to Scrape, with INR and GBP clearly labeled.'),
       ('03  Ask Everyday','Find books, compare on request and ask questions about store policies.'),
       ('04  Build your bag','Add requested books through chat or manage quantities in the storefront.'),
       ('05  Save an order','Review your bag and shipping details, then create an unpaid order.'),
       ('06  Find your order details','View order history or ask the assistant about your own purchases.'),
    ]
    for i,(heading,body) in enumerate(features):
        x=54 if i%2==0 else w/2+28
        y=476-(i//2)*110
        c.setFont('Bold',17);c.setFillColor(GREEN);c.drawString(x,y,heading)
        p=Paragraph(escape(body),ParagraphStyle('poster',fontName='Body',fontSize=12.5,leading=18,textColor=MUTED))
        _,ph=p.wrap(w/2-100,100);p.drawOn(c,x,y-13-ph)
    c.setStrokeColor(LINE);c.line(54,137,w-54,137)
    c.setFillColor(INK);c.setFont('Bold',11)
    c.drawString(54,112,'FastAPI  /  SQLite  /  LangChain  /  Beautiful Soup  /  FAISS')
    c.setFont('Body',10);c.setFillColor(MUTED)
    c.drawString(54,87,'Local demo: http://127.0.0.1:5173  |  Sign in for your bag, chat and orders')
    c.setFont('Body',9)
    c.drawString(54,57,'Checkout records unpaid orders; no online payments or shipment tracking.')
    c.drawString(54,42,'Books to Scrape uses demo prices. Illustration is concept artwork.')
    c.save()

def render():
    thumbs=[]
    for filename in ['Everyday-LLD.pdf','Everyday-Project-Prompt.pdf','Everyday-Poster.pdf']:
        doc=fitz.open(OUT/filename)
        print(filename, 'pages:', len(doc))
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(1.3,1.3),alpha=False)
            path=QA/(Path(filename).stem+f'-{i+1}.png');pix.save(path)
            for block in page.get_text('blocks'):
                x0,y0,x1,y1,*_=block
                if x0 < 20 or x1 > page.rect.width-15 or y0 < 15 or y1 > page.rect.height-15:
                    raise RuntimeError(f'Out of page content: {filename}, page {i+1}, {block}')
            if filename=='Everyday-Poster.pdf':
                page.get_pixmap(matrix=fitz.Matrix(2.35,2.35),alpha=False).save(OUT/'Everyday-Poster.png')
            else:
                im=Image.open(path).convert('RGB');im.thumbnail((350,495))
                thumb=Image.new('RGB',(374,530),'#e5e5e1');thumb.paste(im,((374-im.width)//2,12))
                ImageDraw.Draw(thumb).text((12,510),f'{Path(filename).stem} / {i+1}',fill='#24362c')
                thumbs.append(thumb)
    contact=Image.new('RGB',(374*4,530*((len(thumbs)+3)//4)),'#d8d8d2')
    for i,thumb in enumerate(thumbs): contact.paste(thumb,((i%4)*374,(i//4)*530))
    contact.save(QA/'contact.png')

for stem,title in [('Everyday-LLD','Low-Level Design'),('Everyday-Project-Prompt','Development Assistance Prompts')]:
    source=ROOT/'docs/project'/f'{stem}.md'
    document(source,title)
    shutil.copyfile(source,OUT/source.name)
poster()
render()
