#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 卫星数据可视化大屏系统 · 课程设计汇报 PPT v2（覆盖全面 / 言简意赅 / 中心突出 / 亮点鲜明）
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from PIL import Image
import os

OUT = '/root/卫星数据可视化大屏系统_课堂汇报_v2.pptx'
prs = Presentation(); prs.slide_width=Inches(13.333333); prs.slide_height=Inches(7.5)
W,H=13.333333,7.5
NAVY='050D18'; PANEL='0B1B2A'; CYAN='36D8EC'; BLUE='4C8DFF'; WHITE='E7F5FC'; MUTED='88A9BD'; GREEN='51DDBB'; ORANGE='FFBF75'; PURPLE='B29AFF'; RED='FF8C83'
FONT='Noto Sans CJK SC'; NUM='Barlow Condensed'

def rgb(h): return RGBColor.from_string(h)
def box(slide,x,y,w,h,fill=PANEL,line=None,radius=False):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid();s.fill.fore_color.rgb=rgb(fill)
    if line: s.line.color.rgb=rgb(line);s.line.width=Pt(.8)
    else: s.line.fill.background()
    return s
def text(slide,txt,x,y,w,h,size=18,color=WHITE,bold=False,font=FONT,align=PP_ALIGN.LEFT,margin=0):
    s=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=s.text_frame;tf.clear();tf.word_wrap=True
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=Inches(margin)
    p=tf.paragraphs[0];p.alignment=align;p.space_after=Pt(0)
    r=p.add_run();r.text=txt;r.font.name=font;r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=rgb(color)
    return s
def rich(slide,parts,x,y,w,h,size=18,align=PP_ALIGN.LEFT):
    s=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=s.text_frame;tf.clear();tf.word_wrap=True
    p=tf.paragraphs[0];p.alignment=align
    for t,c,b in parts:
        r=p.add_run();r.text=t;r.font.name=FONT;r.font.size=Pt(size);r.font.bold=b;r.font.color.rgb=rgb(c)
    return s
def line(slide,x1,y1,x2,y2,color='234459',width=1,dash=False):
    s=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2));s.line.color.rgb=rgb(color);s.line.width=Pt(width)
    if dash:s.line.dash_style=MSO_LINE_DASH_STYLE.DASH
    return s
def circle(slide,txt,x,y,d,fill='0F3044',color=CYAN,size=18):
    s=slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d));s.fill.solid();s.fill.fore_color.rgb=rgb(fill);s.line.color.rgb=rgb(color);s.line.width=Pt(1)
    tf=s.text_frame;tf.clear();tf.vertical_anchor=MSO_ANCHOR.MIDDLE;p=tf.paragraphs[0];p.alignment=PP_ALIGN.CENTER;r=p.add_run();r.text=txt;r.font.name=FONT;r.font.size=Pt(size);r.font.bold=True;r.font.color.rgb=rgb(color)
    return s
def base(title,sub,num):
    s=prs.slides.add_slide(prs.slide_layouts[6]);bg=s.background.fill;bg.solid();bg.fore_color.rgb=rgb(NAVY)
    box(s,0,0,13.333,.06,CYAN);text(s,'SATELLITE INTELLIGENCE  /  COURSE PROJECT',.55,.28,7,.25,8,MUTED,False,NUM)
    text(s,title,.55,.64,11.8,.48,27,WHITE,True);text(s,sub,.57,1.2,11.5,.28,10,MUTED)
    line(s,.55,1.61,12.78,1.61)
    text(s,f'{num:02d}',12.2,.65,.55,.35,15,CYAN,True,NUM,PP_ALIGN.RIGHT)
    text(s,'星轨 · 卫星数据可视化大屏系统',.55,7.12,6,.2,8,MUTED)
    text(s,'VUE 3  ×  FASTAPI  ×  SQLITE  ×  WEBSOCKET',8.0,7.12,4.75,.2,8,MUTED,False,NUM,PP_ALIGN.RIGHT)
    return s
def bullets(slide,items,x,y,w,row=.62,size=15):
    for i,item in enumerate(items):
        circle(slide,str(i+1),x,y+i*row,.28,'0C2C3C',CYAN,10)
        text(slide,item,x+.43,y-.01+i*row,w-.43,row-.04,size,WHITE)
def card(slide,x,y,w,h,title_,body,accent=CYAN,metric=None):
    box(slide,x,y,w,h,PANEL,'1E4057');box(slide,x,y,.035,h,accent)
    text(slide,title_,x+.23,y+.2,w-.45,.3,14,accent,True)
    if metric:text(slide,metric,x+.23,y+.63,w-.45,.56,30,WHITE,True,NUM)
    text(slide,body,x+.23,y+(.72 if not metric else 1.32),w-.45,h-(.92 if not metric else 1.5),11,MUTED)
def pill(slide,txt,x,y,w,color=CYAN):
    box(slide,x,y,w,.33,'0C2638',color,True);text(slide,txt,x,y+.055,w,.2,9,color,True,FONT,PP_ALIGN.CENTER)
def add_image_fit(slide,path,x,y,w,h):
    im=Image.open(path);iw,ih=im.size;ratio=min(w/iw,h/ih);nw,nh=iw*ratio,ih*ratio
    slide.shapes.add_picture(path,Inches(x+(w-nw)/2),Inches(y+(h-nh)/2),Inches(nw),Inches(nh))

# ========== 1 封面 ==========
s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(NAVY)
for d,c in [(5.8,'12354A'),(4.8,'174A60'),(3.7,'1A6375')]:
    sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(8.1+(5.8-d)/2),Inches(.65+(5.8-d)/2),Inches(d),Inches(d));sh.fill.background();sh.line.color.rgb=rgb(c);sh.line.width=Pt(1)
circle(s,'S',9.67,2.21,2.65,'0A2B40',CYAN,56)
line(s,7.8,5.7,12.9,1.0,CYAN,1.4);circle(s,'',12.32,1.12,.18,CYAN,WHITE,1)
text(s,'SATELLITE  /  INTELLIGENCE  /  REALTIME',.7,.65,6.8,.25,11,CYAN,False,NUM)
text(s,'星轨',.7,1.38,5.5,.62,38,WHITE,True)
text(s,'卫星数据可视化大屏系统',.68,2.13,7.4,.8,31,WHITE,True)
text(s,'从真实轨道数据，到可交互的空间态势',.72,3.12,6.7,.38,16,MUTED)
line(s,.72,3.78,5.7,3.78,CYAN,2)
pill(s,'Vue 3',.72,4.18,1.05);pill(s,'FastAPI',1.93,4.18,1.25);pill(s,'WebSocket',3.35,4.18,1.55);pill(s,'Three.js',5.08,4.18,1.35)
text(s,'课程设计汇报',.72,5.25,2.2,.3,14,WHITE,True)
text(s,'汇报人：陈壮壮    ｜    小组：________    ｜    日期：2026.11',.72,5.75,6.7,.3,12,MUTED)
text(s,'PUBLIC DEMO  ·  heyckz.cc/satdash/',.72,6.72,6.5,.25,10,CYAN,False,NUM)

# ========== 2 项目概述（中心：解决什么问题）==========
s=base('01  项目概述｜我们解决了什么问题？','真实数据 · 三层架构 · 实时推送 · 故障可降级',2)
text(s,'面向展厅 / 指挥中心的多指标卫星态势大屏',.62,1.9,8,.42,20,WHITE,True)
text(s,'把分散的卫星目录、ISS 位置与空间天气，统一为可读、可查、可追踪的可视化系统。',.62,2.42,11.9,.4,13,MUTED)
card(s,.62,3.08,2.86,2.7,'真实在轨目标','CelesTrak 在轨 TLE 与 SatCat 目录，后端采集并入库。',CYAN,'15,875')
card(s,3.72,3.08,2.86,2.7,'实时数据链路','ISS 每 10 秒采集，通过 WebSocket 主动推送。',GREEN,'10 s')
card(s,6.82,3.08,2.86,2.7,'持久化业务表','卫星 / 位置 / 天气 / 观测 / 采集日志。',PURPLE,'5 张')
card(s,9.92,3.08,2.86,2.7,'自动接口验收','鉴权、分页、写入、聚合、实时与数据库。',ORANGE,'13 / 13')
box(s,.62,6.16,12.16,.54,'0B2431','1B5366');text(s,'核心目标：不是“画一张大屏”，而是完成一套可部署、可验证的前后端系统。',.85,6.31,11.6,.25,13,CYAN,True)

# ========== 3 系统演示 ==========
s=base('02  系统演示｜一屏掌握空间态势','公网真实运行画面 · 1920 × 1080 等比缩放',3)
box(s,.55,1.84,12.23,4.95,'02070D','28536B');add_image_fit(s,'/root/satdash/public-dashboard.png',.62,1.91,12.09,4.81)
pill(s,'① 在轨规模',.65,6.48,1.6);pill(s,'② 轨道分布',2.43,6.48,1.6);pill(s,'③ 三维地球',4.21,6.48,1.6,GREEN);pill(s,'④ 实时遥测',5.99,6.48,1.6,GREEN);pill(s,'⑤ 卫星目录',7.77,6.48,1.6,PURPLE);pill(s,'⑥ 空间天气',9.55,6.48,1.6,ORANGE)
text(s,'heyckz.cc/satdash/',10.88,6.56,1.86,.2,8,CYAN,False,NUM,PP_ALIGN.RIGHT)

# ========== 4 系统架构 ==========
s=base('03  系统架构｜职责清晰的三层设计','前端只负责展示与交互；业务计算、密钥与缓存全部在后端',4)
for x,t,sub,c in [(.7,'前端展示层','Vue 3 / ECharts / Three.js',CYAN),(4.75,'后端业务层','FastAPI / APScheduler / JWT',GREEN),(8.8,'数据与外部服务','SQLite / CelesTrak / ISS / NOAA',PURPLE)]:
    box(s,x,2.0,3.75,.72,'0D2637',c);text(s,t,x+.18,2.15,3.4,.25,16,c,True);text(s,sub,x+.18,2.49,3.4,.2,8,MUTED,False,NUM)
for x,items,c in [(.7,['大屏等比缩放','图表与三维渲染','登录与观测录入','WebSocket 断线重连'],CYAN),(4.75,['JWT 登录鉴权','聚合统计 / 分页查询','第三方代理与 TTL 缓存','定时采集 / 实时广播'],GREEN),(8.8,['5 张 SQLite 业务表','TLE 每 2 小时刷新','ISS 每 10 秒刷新','NOAA 空间天气'],PURPLE)]:
    box(s,x,2.9,3.75,2.65,PANEL,'1B3C52')
    for i,it in enumerate(items): circle(s,'',x+.22,3.21+i*.55,.09,c,c,1);text(s,it,x+.46,3.1+i*.55,3.0,.32,12,WHITE)
text(s,'HTTPS  /  JSON',3.72,3.52,1.1,.22,9,CYAN,False,NUM,PP_ALIGN.CENTER);text(s,'→',4.15,3.86,.45,.42,25,CYAN,True,FONT,PP_ALIGN.CENTER)
text(s,'SQL  /  HTTP',7.82,3.52,1.0,.22,9,GREEN,False,NUM,PP_ALIGN.CENTER);text(s,'→',8.21,3.86,.45,.42,25,GREEN,True,FONT,PP_ALIGN.CENTER)
box(s,.7,5.95,11.85,.67,'0B2431','1B5366');text(s,'统一入口：https://heyckz.cc/satdash/    →    Nginx 同源转发 /satdash/api 与 /satdash/ws',.96,6.16,11.3,.27,12,CYAN,True)

# ========== 5 核心流程 ==========
s=base('04  核心流程｜从第三方数据到实时大屏','密钥不进入前端；采集、缓存、入库与推送形成闭环',5)
steps=[('01','第三方数据源','CelesTrak / ISS / NOAA'),('02','后端定时采集','TLE 2h · ISS 10s'),('03','缓存与持久化','TTL 缓存 · SQLite'),('04','业务接口','聚合 / 分页 / 鉴权'),('05','WebSocket 推送','增量数据 · 自动重连')]
for i,(n,t,b) in enumerate(steps):
    x=.55+i*2.53;circle(s,n,x+.62,2.13,.7,'0C2C3D',CYAN if i<4 else GREEN,15)
    if i<4:text(s,'→',x+1.8,2.22,.45,.35,21,MUTED,False,FONT,PP_ALIGN.CENTER)
    text(s,t,x,3.08,1.95,.35,14,WHITE,True,FONT,PP_ALIGN.CENTER);text(s,b,x,3.55,1.95,.5,10,MUTED,False,FONT,PP_ALIGN.CENTER)
box(s,.62,4.6,12.1,1.6,PANEL,'1E4057')
text(s,'为什么要 WebSocket？',.9,4.87,3.2,.32,16,CYAN,True)
text(s,'服务端采集到新位置后主动推送，避免前端高频全量轮询。',.9,5.36,5.25,.4,12,WHITE)
line(s,6.53,4.88,6.53,5.92,'24465C')
text(s,'断线怎么办？',6.87,4.87,2.5,.32,16,GREEN,True)
text(s,'保留最近数据 + 状态提示 + 3 秒自动重连，不白屏。',6.87,5.36,5.25,.4,12,WHITE)

# ========== 6 功能亮点（新增：一屏看全亮点）==========
s=base('05  功能亮点｜从“能看”到“能用”','多卫星追踪 · 历史回放 · 覆盖分析 · 天气告警 · 数据导出',6)
highlights=[('多卫星实时追踪','同时追踪 ISS / HST / NOAA-18/19/20 / SUOMI NPP 六颗卫星，真实 API + SGP4 推算双通道。',CYAN,'6 颗'),
            ('历史轨迹回放','时间轴控制 ISS 历史轨迹动画播放 / 暂停 / 重置，数据全部来自数据库回查。',GREEN,'回放'),
            ('覆盖范围可视化','Three.js 地球实时绘制卫星对地覆盖圆，直观展示可见范围与覆盖直径。',PURPLE,'覆盖圆'),
            ('空间天气告警','Kp 指数≥4 触发琥珀/红色告警条并闪烁提示，模拟 DONKI 告警通知。',ORANGE,'告警')]
for i,(t,b,c,m) in enumerate(highlights):
    x=.62+(i%2)*6.16; y=1.95+(i//2)*2.05
    card(s,x,y,5.8,1.8,t,b,c,m)
box(s,.62,6.15,12.16,.52,'0B2431','1B5366');text(s,'另有：每日天文一图（APOD 三源兜底）· CSV 导出 · 整屏截图导出 · TypeScript 工程化',.88,6.28,11.4,.25,12,CYAN,True)

# ========== 7 关键难点（中心：外部失败系统不失败）==========
s=base('06  关键难点｜外部接口失败，系统也不能失败','不用固定假数据；每一种降级都向用户明确标识',7)
card(s,.65,1.95,3.75,3.72,'① 第三方接口不稳定','TTL 缓存 + 最近成功缓存 + 随项目附带的真实 TLE 快照。外部故障时返回 degraded/message，不直接抛 500。',CYAN)
card(s,4.78,1.95,3.75,3.72,'② ISS 无网络也要可展示','在线 API 失败时，后端读取真实 TLE，使用 SGP4 计算当前位置；页面明确显示“降级推算”。',GREEN)
card(s,8.91,1.95,3.75,3.72,'③ 大屏适配与连接恢复','1920×1080 舞台等比缩放；图表 ResizeObserver；WebSocket 断开 3 秒重连，保留最近数据。',PURPLE)
box(s,.65,6.02,12.01,.66,'10252B','276352');text(s,'设计原则：宁可明确“当前是缓存 / 推算”，也不把过期或模拟数据冒充实时数据。',.93,6.21,11.45,.28,13,GREEN,True)

# ========== 8 数据库设计 ==========
s=base('07  数据库设计｜不仅能看，还能留存与回查','SQLite 事务 / 外键 / 索引；适合课程单实例部署',8)
circle(s,'卫星\n目录',5.55,3.03,1.45,'103149',CYAN,20)
for x,y,t,sub,c in [(1.0,2.0,'satellites','NORAD 主键 · 名称 · 轨道参数',CYAN),(8.9,1.98,'iss_positions','卫星外键 · 经纬度 · 时间索引',GREEN),(1.0,4.55,'observations','观测人 · 备注 · 卫星外键',PURPLE),(8.9,4.55,'space_weather','Kp 指数 · 等级 · 时间唯一',ORANGE)]:
    box(s,x,y,3.35,1.16,PANEL,c);text(s,t,x+.2,y+.18,2.95,.28,15,c,True,NUM);text(s,sub,x+.2,y+.65,2.95,.25,10,MUTED)
line(s,4.35,2.58,5.55,3.35,CYAN,1.3);line(s,7.0,3.35,8.9,2.58,GREEN,1.3);line(s,4.35,5.05,5.55,4.05,PURPLE,1.3);line(s,7.0,4.05,8.9,5.05,ORANGE,1.3)
box(s,4.53,5.27,3.5,.79,'111E2D','315066');text(s,'collection_logs',4.73,5.42,3.1,.25,14,MUTED,True,NUM,PP_ALIGN.CENTER);text(s,'采集来源 · 状态 · 数量',4.73,5.75,3.1,.2,9,MUTED,False,FONT,PP_ALIGN.CENTER)
box(s,.72,6.36,11.86,.42,'0B2431');text(s,'演示闭环：POST 观测记录 → 外键校验 → SQLite 落库 → GET 台账回查',.95,6.46,11.4,.22,12,CYAN,True,FONT,PP_ALIGN.CENTER)

# ========== 9 工程部署 ==========
s=base('08  工程化部署｜从本机运行到公网访问','Docker Compose + Nginx + HTTPS；不影响既有平台',9)
for i,(t,b,c) in enumerate([('构建前端','Vue 3 生产构建\n字体本地打包',CYAN),('启动后端','FastAPI 健康检查\n定时任务常驻',GREEN),('同源反向代理','页面 / API / WS\n统一子路径',PURPLE),('公网 HTTPS','heyckz.cc/satdash/\n证书与域名复用',ORANGE)]):
    x=.65+i*3.06;box(s,x,2.0,2.72,1.55,PANEL,c);text(s,f'0{i+1}',x+.2,2.2,.5,.3,17,c,True,NUM);text(s,t,x+.2,2.67,2.3,.28,14,WHITE,True);text(s,b,x+.2,3.08,2.3,.5,10,MUTED)
    if i<3:text(s,'→',x+2.72,2.62,.34,.35,20,MUTED,False,FONT,PP_ALIGN.CENTER)
text(s,'部署中实际解决的问题',.68,4.13,4.2,.32,17,WHITE,True)
bullets(s,['容器无法访问 PyPI → 切换国内镜像源','APScheduler 工作线程无 loop → run_coroutine_threadsafe','原子替换配置导致旧 inode 挂载 → 重启 Nginx','双层子路径转发不一致 → 页面/API/WS 路径统一'],.72,4.72,11.8,.46,12)

# ========== 10 测试验收 ==========
s=base('09  测试与验收｜结果可复现，而非口头保证','自动化接口测试 + 浏览器真实渲染 + 公网回归',10)
circle(s,'13/13',.8,2.02,2.12,'0D3038',GREEN,30);text(s,'后端接口验收全部通过',.62,4.36,2.55,.55,14,GREEN,True,FONT,PP_ALIGN.CENTER)
checks=[('鉴权','登录签发 Token；未登录 401'),('查询','分页 / 关键词 / 聚合统计'),('写入','观测落库并可回查'),('实时','WebSocket 推送与非法 Token 拒绝'),('渲染','5 个 Canvas · 8 行卫星目录'),('适配','1920×1080 无滚动条'),('控制台','0 JavaScript 错误'),('公网','HTTPS 页面 / API / WS 全通过')]
for i,(t,b) in enumerate(checks):
    col=i%2;row=i//2;x=3.85+col*4.45;y=1.94+row*1.05
    box(s,x,y,4.12,.82,PANEL,'1E4057');circle(s,'✓',x+.16,y+.21,.35,'10352F',GREEN,12);text(s,t,x+.65,y+.14,.72,.22,12,WHITE,True);text(s,b,x+1.39,y+.14,2.52,.46,10,MUTED)
box(s,.68,6.42,11.95,.37,'0B2431');text(s,'部署后同步复验：数字藏经阁 /llmops/ 保持 200，根域名 302，互不影响。',.93,6.5,11.4,.2,11,CYAN,True,FONT,PP_ALIGN.CENTER)

# ========== 11 特色与分工 ==========
s=base('10  项目特色与团队分工','把“数据大屏”做成完整、可解释、可部署的工程作品',11)
text(s,'项目特色',.68,1.94,3,.3,18,CYAN,True)
bullets(s,['真实公共数据，不依赖付费 API','三层职责明确，密钥只在后端','实时推送 + 历史留存 + 业务写入','缓存与 SGP4 降级，兼顾稳定性与诚实性','Docker 一键部署，自动验收可复现'],.72,2.52,5.5,.66,13)
line(s,6.5,1.98,6.5,6.5,'25455B')
text(s,'建议分工',6.88,1.94,3,.3,18,GREEN,True)
card(s,6.88,2.5,5.72,1.03,'前端 1–2 人','大屏布局、ECharts、Three.js、WebSocket 接入',CYAN)
card(s,6.88,3.78,5.72,1.03,'后端 1–2 人','数据代理与缓存、聚合接口、定时任务、实时推送',GREEN)
card(s,6.88,5.06,5.72,1.03,'统筹 1 人','数据库、接口联调、部署、测试记录与答辩材料',PURPLE)
text(s,'※ 汇报前请将本页分工替换为真实成员与贡献。',6.91,6.4,5.5,.24,10,ORANGE)

# ========== 12 收获展望 ==========
s=base('11  实训收获与后续展望','从“会写页面”走向“能交付系统”',12)
card(s,.68,1.96,3.76,3.65,'技术收获','理解前后端边界、JWT 鉴权、数据库外键与索引；掌握 WebSocket、定时任务、ECharts 与 Three.js 的协同。',CYAN)
card(s,4.79,1.96,3.76,3.65,'工程收获','真实定位依赖源、异步事件循环、Nginx 子路径与容器挂载问题；用自动测试证明改动有效。',GREEN)
card(s,8.9,1.96,3.76,3.65,'协作收获','以接口约定推进并行开发；记录采集来源与降级状态；把部署、文档和答辩纳入完整交付。',PURPLE)
text(s,'下一步可扩展',.7,6.0,2.0,.3,14,WHITE,True)
pill(s,'PostgreSQL / Redis',2.55,5.96,2.05);pill(s,'CesiumJS 精确轨道',4.85,5.96,2.05,GREEN);pill(s,'NASA 近地天体',7.15,5.96,1.8,PURPLE);pill(s,'权限分级与审计',9.2,5.96,1.95,ORANGE)

# ========== 13 结束 ==========
s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(NAVY)
text(s,'THANK YOU',.7,.62,3,.3,13,CYAN,False,NUM)
text(s,'谢谢聆听 · 欢迎提问',.68,1.46,7.6,.7,34,WHITE,True)
text(s,'让每一颗卫星，都有可见的轨迹。',.72,2.48,6.5,.4,17,MUTED)
line(s,.72,3.22,5.8,3.22,CYAN,2)
box(s,.72,3.76,6.1,1.17,'0B2431','24536B');text(s,'在线演示',.98,3.99,1.3,.25,12,MUTED);text(s,'https://heyckz.cc/satdash/',.98,4.4,5.45,.32,17,CYAN,True,NUM)
text(s,'演示登录：数字藏经阁统一邮箱账号（LLMOps 统一认证）',.75,5.35,5.9,.28,12,WHITE)
for d,c in [(4.7,'12354A'),(3.7,'174A60'),(2.7,'1A6375')]:
    sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(8.05+(4.7-d)/2),Inches(1.35+(4.7-d)/2),Inches(d),Inches(d));sh.fill.background();sh.line.color.rgb=rgb(c);sh.line.width=Pt(1)
circle(s,'S',9.42,2.72,1.95,'0A2B40',CYAN,42)
text(s,'Q  &  A',9.02,5.48,2.9,.42,23,CYAN,True,NUM,PP_ALIGN.CENTER)
text(s,'星轨 · 卫星数据可视化大屏系统',.72,6.88,6.5,.25,10,MUTED)

# 文档属性
prs.core_properties.title='星轨 · 卫星数据可视化大屏系统｜课程设计汇报'
prs.core_properties.subject='Vue3 + FastAPI + SQLite + WebSocket + Three.js'
prs.core_properties.author='陈壮壮'
prs.core_properties.keywords='卫星, 数据大屏, 课程设计, 前后端, WebSocket'
prs.save(OUT)
print(OUT, len(prs.slides), os.path.getsize(OUT))
