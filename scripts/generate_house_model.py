# -*- coding: utf-8 -*-
# Генерация 3D-модели: границы участка (ГПЗУ), существующий дом (на снос) и новый дом.
# Все входные данные из ТЗ v2.0 (data/TZ_V2.0.odt) и первоисточников (ГПЗУ, тех.паспорт БТИ).
# Запуск: см. data/HOW_TO_RUN.md

import FreeCAD as App
import Part
import Arch
import math

M = 1000.0  # 1 метр = 1000 мм (внутренние единицы FreeCAD - миллиметры)

# =====================================================================
# ВХОДНЫЕ ПАРАМЕТРЫ - редактируйте только этот блок
# =====================================================================

# --- Границы участка (ГПЗУ №РФ-62-4-13-2-09-2026-1872-0, Приложение 1) ---
# Координаты точек 1-15 в местной системе координат ЕГРН (X, Y), метры.
PLOT_BOUNDARY_POINTS = [
    (468097.60, 1333222.78),  # точка 1
    (468077.27, 1333266.80),  # точка 2
    (468029.30, 1333255.38),  # точка 3
    (468031.37, 1333249.78),  # точка 4
    (468033.51, 1333243.77),  # точка 5
    (468037.13, 1333238.85),  # точка 6
    (468040.49, 1333231.97),  # точка 7
    (468042.52, 1333226.88),  # точка 8
    (468046.52, 1333217.79),  # точка 9
    (468051.05, 1333207.12),  # точка 10
    (468051.80, 1333205.55),  # точка 11
    (468061.94, 1333209.65),  # точка 12
    (468077.04, 1333215.69),  # точка 13
    (468078.17, 1333215.04),  # точка 14
    (468096.30, 1333222.26),  # точка 15
]
STREET_EDGE = (0, 1)  # индексы точек, между которыми проходит улица (точки 1-2)

# --- Существующий дом (снос после стройки нового, тех.паспорт БТИ инв.№13975) ---
# Уточнено пользователем на месте: расстояние от точки 1 до ПРАВОГО (ближнего к точке 2)
# угла старого дома = 22 м; отступ обоих домов от линии 1-2 = 1 м.
# ⚠ 1 м от линии улицы заметно меньше, чем "не менее 5 м от красной линии", упомянутых в
# ТЗ v2.0 (раздел 2) - для НОВОГО дома эту цифру стоит сверить с ПЗЗ поселения перед подачей
# документов на согласование (см. ТЗ v2.0, раздел 7). Для старого дома - это факт на местности.
OLD_HOUSE_LENGTH = 9.4              # м, вдоль уличного фасада (оценка по общему контуру БТИ)
OLD_HOUSE_DEPTH = 13.0              # м, вглубь участка (оценка по общему контуру БТИ)
OLD_HOUSE_RIGHT_CORNER_FROM_PT1 = 22.0  # м, от точки 1 до правого (ближнего к точке 2) угла дома
OLD_HOUSE_SETBACK_FROM_STREET = 1.0     # м, от линии улицы (точки 1-2) до уличного фасада
OLD_HOUSE_OFFSET_ALONG_STREET = OLD_HOUSE_RIGHT_CORNER_FROM_PT1 - OLD_HOUSE_LENGTH  # левый угол

# --- Новый дом (ТЗ v2.0, разделы 1-3) ---
NEW_HOUSE_LENGTH = 12.0   # м, уличный фасад, максимум по ГПЗУ п.13.1.22.5
NEW_HOUSE_WIDTH = 8.0     # м, боковой фасад, максимум по ГПЗУ п.13.1.22.5
WALL_THICKNESS = 0.30     # м, наружная стена каркаса (доска+утеплитель+вагонка), уточняется теплорасчётом
EAVE_HEIGHT = 3.0         # м, высота стен до карниза
ROOF_ANGLE_DEG = 35.0     # градусы, уклон кровли (регламент: 30-40°), вальмовая без светёлки
ROOF_THICKNESS = 0.15     # м, толщина кровельного пирога
ROOF_OVERHANG = 0.4       # м, вынос свеса кровли за плоскость стены
PARTITION_THICKNESS = 0.10  # м, внутренние перегородки

# --- Планировка (эскиз data/house_scetch_v1.0.jpg) ---
# Координаты ниже - в СОБСТВЕННОЙ системе дома: house_x 0..12000 мм (0 = торец у входа/
# со стороны старого дома и точки 1, 12000 = дальний торец со стороны точки 2 - спальни),
# house_y 0..8000 мм (0 = уличный/передний фасад, 8000 = задняя стена).
# Санузел и котельная зеркально поменяны местами со спальней 10.64 м2 (см. чат) относительно
# исходного эскиза.

# Технологический зазор между новым фундаментом и существующим домом на время стройки
CONSTRUCTION_CLEARANCE = 5.0  # м, подтверждено застройщиком (ТЗ v2.0, раздел 2.1)
NEW_HOUSE_DIRECTION = 1  # +1 = смещение в сторону точки 2, -1 = в сторону точки 1

OUTPUT_FILE = "../output/House_Draft_v1.FCStd"

# =====================================================================
# РАСЧЁТ ЛОКАЛЬНОЙ СИСТЕМЫ КООРДИНАТ
# Начало (0,0) = точка 1. Ось X - вдоль улицы (точка1 -> точка2). Ось Y - вглубь участка.
# =====================================================================

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])

def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]

def _unit(a):
    n = math.hypot(a[0], a[1])
    return (a[0] / n, a[1] / n)

i1, i2 = STREET_EDGE
origin = PLOT_BOUNDARY_POINTS[i1]
u = _unit(_sub(PLOT_BOUNDARY_POINTS[i2], origin))  # локальная ось X (вдоль улицы)
v = (-u[1], u[0])  # перпендикуляр (кандидат для локальной оси Y)

# Направление v проверяем по центроиду участка - оно должно указывать внутрь участка
cx = sum(p[0] for p in PLOT_BOUNDARY_POINTS) / len(PLOT_BOUNDARY_POINTS)
cy = sum(p[1] for p in PLOT_BOUNDARY_POINTS) / len(PLOT_BOUNDARY_POINTS)
if _dot(_sub((cx, cy), origin), v) < 0:
    v = (-v[0], -v[1])

def to_local(p):
    rel = _sub(p, origin)
    return (_dot(rel, u), _dot(rel, v))

plot_local = [to_local(p) for p in PLOT_BOUNDARY_POINTS]
street_length = math.hypot(*_sub(PLOT_BOUNDARY_POINTS[i2], origin))
print("Длина уличной границы участка (точки 1-2): %.2f м" % street_length)

# --- Перевод в координаты отображения ---
# to_local() даёт (X вдоль улицы 1->2, Y - положительный вглубь участка).
# Для показа по требованию: линия улицы (Y=0) должна быть ВЕРХНЕЙ горизонталью плана,
# точка 1 - слева, точка 2 - справа. Поэтому на экране Y_display = -Y_local (зеркало).
def disp_xy(x, y):
    return (x, -y)

def rect_ccw_mirrored(x0, y0, Lx, Ly, z):
    # Прямоугольник (x0,y0)-(x0+Lx,y0+Ly) в логических координатах (Y - вглубь участка).
    # Обход вершин разворачивается в обратном порядке ПЕРЕД зеркалированием Y, чтобы после
    # зеркала получился корректный обход против часовой стрелки - это важно для Arch.makeRoof,
    # иначе скат крыши строится некорректно (проверено эмпирически).
    logical = [(x0, y0), (x0 + Lx, y0), (x0 + Lx, y0 + Ly), (x0, y0 + Ly)]
    logical.reverse()
    pts = []
    for (x, y) in logical:
        dx, dy = disp_xy(x, y)
        pts.append(App.Vector(dx * M, dy * M, z * M))
    return pts

# =====================================================================
# ПОСТРОЕНИЕ МОДЕЛИ
# =====================================================================

doc = App.newDocument("House_Site_Plan")

# --- 1. Граница участка ---
plot_pts_3d = [App.Vector(disp_xy(x, y)[0] * M, disp_xy(x, y)[1] * M, 0) for (x, y) in plot_local]
plot_pts_3d.append(plot_pts_3d[0])
plot_boundary = doc.addObject("Part::Feature", "Uchastok_Granitsa_2500m2")
plot_boundary.Shape = Part.makePolygon(plot_pts_3d)

# --- 2. Существующий дом (на снос) ---
ox0 = OLD_HOUSE_OFFSET_ALONG_STREET
oy0 = OLD_HOUSE_SETBACK_FROM_STREET
old_pts = rect_ccw_mirrored(ox0, oy0, OLD_HOUSE_LENGTH, OLD_HOUSE_DEPTH, 0)
old_pts.append(old_pts[0])
old_house = doc.addObject("Part::Feature", "Sushestvuyushiy_Dom_SNOS_posle_stroyki")
old_house.Shape = Part.Face(Part.makePolygon(old_pts))

# --- 3. Новый дом: посадка по правилам ТЗ v2.0 ---
# Уличный фасад нового дома - на той же оси (том же отступе от улицы), что и старый дом.
new_y0 = oy0
if NEW_HOUSE_DIRECTION >= 0:
    new_x0 = ox0 + OLD_HOUSE_LENGTH + CONSTRUCTION_CLEARANCE
else:
    new_x0 = ox0 - CONSTRUCTION_CLEARANCE - NEW_HOUSE_LENGTH

centerline_length = NEW_HOUSE_LENGTH - WALL_THICKNESS
centerline_width = NEW_HOUSE_WIDTH - WALL_THICKNESS
cx0 = new_x0 + WALL_THICKNESS / 2.0
cy0 = new_y0 + WALL_THICKNESS / 2.0

wall_centerline_pts = rect_ccw_mirrored(cx0, cy0, centerline_length, centerline_width, 0)
wall_centerline_pts.append(wall_centerline_pts[0])
wall_path = doc.addObject("Part::Feature", "Novyy_Dom_Os_Sten")
wall_path.Shape = Part.makePolygon(wall_centerline_pts)

new_walls = Arch.makeWall(wall_path, height=EAVE_HEIGHT * M, width=WALL_THICKNESS * M, align="Center")
new_walls.Label = "Novyy_Dom_Steny"
doc.recompute()

# Кровля - вальмовая, строится по внешнему контуру стен на отметке карниза.
roof_outer_pts = rect_ccw_mirrored(new_x0, new_y0, NEW_HOUSE_LENGTH, NEW_HOUSE_WIDTH, EAVE_HEIGHT)
roof_outer_pts.append(roof_outer_pts[0])
roof_base = doc.addObject("Part::Feature", "Novyy_Dom_Kontur_Krovli")
roof_base.Shape = Part.Face(Part.makePolygon(roof_outer_pts))

roof_run = (NEW_HOUSE_WIDTH / 2.0) * M  # половина меньшей стороны - конёк точно по центру
new_roof = Arch.makeRoof(
    baseobj=roof_base, facenr=1,
    angles=[ROOF_ANGLE_DEG] * 4,
    run=[roof_run] * 4,
    thickness=[ROOF_THICKNESS * M] * 4,
    overhang=[ROOF_OVERHANG * M] * 4,
)
new_roof.Label = "Novyy_Dom_Krovlya_Valmovaya"
doc.recompute()

# =====================================================================
# ПЛАНИРОВКА ПОМЕЩЕНИЙ (по эскизу, с перестановкой санузла/котельной и спальни 10.64 м2)
# =====================================================================

def house_pt(hx_mm, hy_mm):
    # Перевод из собственных координат дома в ММ (0..12000 x 0..8000) в абсолютные
    # "логические" координаты участка В МЕТРАХ (те же единицы, что new_x0/new_y0).
    return (new_x0 + hx_mm / M, new_y0 + hy_mm / M)

def make_partition(hx1, hy1, hx2, hy2, name, thickness=PARTITION_THICKNESS, height=EAVE_HEIGHT):
    x1, y1 = house_pt(hx1, hy1)
    x2, y2 = house_pt(hx2, hy2)
    dx1, dy1 = disp_xy(x1, y1)
    dx2, dy2 = disp_xy(x2, y2)
    path = doc.addObject("Part::Feature", name + "_Os")
    path.Shape = Part.makePolygon([App.Vector(dx1 * M, dy1 * M, 0), App.Vector(dx2 * M, dy2 * M, 0)])
    wall = Arch.makeWall(path, height=height * M, width=thickness * M, align="Center")
    wall.Label = name
    return wall

def make_room(hx0_mm, hy0_mm, hLx_mm, hLy_mm, name):
    x0, y0 = house_pt(hx0_mm, hy0_mm)
    pts = rect_ccw_mirrored(x0, y0, hLx_mm / M, hLy_mm / M, 0)
    pts.append(pts[0])
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = Part.Face(Part.makePolygon(pts))
    area = (hLx_mm / M) * (hLy_mm / M)
    return obj, area

# --- Внутренние перегородки ---
wall_spalni_kuhnya = make_partition(8000, 0, 8000, 8000, "Peregorodka_Spalni_Kuhnya")       # col1 / col2
wall_mezhdu_spalnyami = make_partition(8000, 4000, 12000, 4000, "Peregorodka_Mezhdu_Spalnyami")  # спальня-спальня
wall_kuhnya_uzel = make_partition(4000, 0, 4000, 8000, "Peregorodka_Kuhnya_Uzel")        # col2 / col3
wall_uzel_prihozhaya = make_partition(0, 3000, 4000, 3000, "Peregorodka_Uzel_Prihozhaya")    # сан/кот <-> прихожая
wall_prihozhaya_spalnya3 = make_partition(0, 4700, 4000, 4700, "Peregorodka_Prihozhaya_Spalnya3")  # прихожая <-> спальня3
wall_sanuzel_kotelnaya = make_partition(1900, 0, 1900, 3000, "Peregorodka_Sanuzel_Kotelnaya")  # санузел <-> котельная
doc.recompute()

# --- Помещения (плоские маркеры для визуальной проверки площадей) ---
rooms = []
rooms.append(make_room(8000, 4000, 4000, 4000, "Spalnya_1_15_59m2"))
rooms.append(make_room(8000, 0, 4000, 4000, "Spalnya_2_15_59m2"))
rooms.append(make_room(4000, 0, 4000, 8000, "Kuhnya_Gostinaya_28_9m2"))
# ПОСЛЕ ПЕРЕСТАНОВКИ: место у входа (бывшее "спальня 10.64") -> санузел + котельная
rooms.append(make_room(1900, 0, 2100, 3000, "Sanuzel_posle_perestanovki"))
rooms.append(make_room(0, 0, 1900, 3000, "Kotelnaya_posle_perestanovki"))
rooms.append(make_room(0, 3000, 4000, 1700, "Prihozhaya_4_04m2"))
# ПОСЛЕ ПЕРЕСТАНОВКИ: место у задней стены (бывшее "санузел+котельная") -> спальня 10.64
rooms.append(make_room(0, 4700, 4000, 3300, "Spalnya_3_10_64m2_posle_perestanovki"))
doc.recompute()

# --- Крыльцо и отметка входа (со стороны точки 1 / старого дома, торец house_x=0) ---
porch_pts = rect_ccw_mirrored(*house_pt(-1950, 3000), 1950 / M, 1700 / M, 0)
porch_pts.append(porch_pts[0])
porch = doc.addObject("Part::Feature", "Krylco_3_30m2")
porch.Shape = Part.Face(Part.makePolygon(porch_pts))

doc.recompute()

# =====================================================================
# ДВЕРНЫЕ И ОКОННЫЕ ПРОЁМЫ
# =====================================================================

def cut_opening(host_wall, hx1, hy1, hx2, hy2, hz0, hz1, name):
    # hx/hy - собственные координаты дома (мм), hz0/hz1 - высота проёма от пола (мм).
    x1, y1 = house_pt(hx1, hy1)
    x2, y2 = house_pt(hx2, hy2)
    dx1, dy1 = disp_xy(x1, y1)
    dx2, dy2 = disp_xy(x2, y2)
    pts = [
        App.Vector(dx1 * M, dy1 * M, hz0),
        App.Vector(dx2 * M, dy2 * M, hz0),
        App.Vector(dx2 * M, dy2 * M, hz1),
        App.Vector(dx1 * M, dy1 * M, hz1),
        App.Vector(dx1 * M, dy1 * M, hz0),
    ]
    prof = doc.addObject("Part::Feature", name + "_Profil")
    prof.Shape = Part.makePolygon(pts)
    opening = Arch.makeWindow(baseobj=prof, name=name)
    opening.Hosts = [host_wall]
    return opening

DOOR_W, DOOR_H = 800.0, 2000.0
ENTRANCE_DOOR_W = 900.0

# --- Двери (внутренние + вход) ---
cut_opening(new_walls, 0, 3850 - ENTRANCE_DOOR_W / 2,
            0, 3850 + ENTRANCE_DOOR_W / 2, 0, DOOR_H, "D1_Vhod")
cut_opening(wall_kuhnya_uzel, 4000, 3850 - DOOR_W / 2, 4000, 3850 + DOOR_W / 2, 0, DOOR_H, "D2_Prihozhaya_Kuhnya")
cut_opening(wall_uzel_prihozhaya, 2950 - DOOR_W / 2, 3000, 2950 + DOOR_W / 2, 3000, 0, DOOR_H, "D3_Prihozhaya_Sanuzel")
cut_opening(wall_uzel_prihozhaya, 950 - DOOR_W / 2, 3000, 950 + DOOR_W / 2, 3000, 0, DOOR_H, "D4_Prihozhaya_Kotelnaya")
cut_opening(wall_prihozhaya_spalnya3, 3700 - DOOR_W, 4700, 3700, 4700, 0, DOOR_H, "D5_Prihozhaya_Spalnya3")  # сдвинута к стене гостиной (300мм зазор)
cut_opening(wall_spalni_kuhnya, 8000, 6000 - DOOR_W / 2, 8000, 6000 + DOOR_W / 2, 0, DOOR_H, "D6_Kuhnya_Spalnya1")
cut_opening(wall_spalni_kuhnya, 8000, 2000 - DOOR_W / 2, 8000, 2000 + DOOR_W / 2, 0, DOOR_H, "D7_Kuhnya_Spalnya2")
doc.recompute()

# --- Окна уличного фасада: схема "три и одно большое" (house_y=0, торец кухни/спальни-2) ---
STD_WIN_W = 800.0
STD_WIN_H = round(STD_WIN_W * 1.73)   # пропорция 1:1,73 по регламенту
BIG_WIN_W = 1200.0
BIG_WIN_H = round(BIG_WIN_W * 1.73)
WIN_SILL = 700.0

for i, cx in enumerate([4700, 6000, 7300], start=1):
    cut_opening(new_walls, cx - STD_WIN_W / 2, 0, cx + STD_WIN_W / 2, 0,
                WIN_SILL, WIN_SILL + STD_WIN_H, "W%d_Kuhnya_Okno" % i)

cut_opening(new_walls, 10000 - BIG_WIN_W / 2, 0, 10000 + BIG_WIN_W / 2, 0,
            WIN_SILL, WIN_SILL + BIG_WIN_H, "W4_Spalnya2_Bolshoe_Okno")

# --- Окно котельной (обязательное требование ТЗ v2.0, не на уличном фасаде) ---
cut_opening(new_walls, 0, 1000 - 300, 0, 1000 + 300, 900, 2100, "W5_Kotelnaya_Okno")

# --- Окна задней стены (house_y=8000): по 2 стандартных в спальню-1 и спальню-3, большое в кухню ---
for i, cx in enumerate([9500, 10500], start=1):
    cut_opening(new_walls, cx - STD_WIN_W / 2, 8000, cx + STD_WIN_W / 2, 8000,
                WIN_SILL, WIN_SILL + STD_WIN_H, "W6_%d_Spalnya1_Okno" % i)

for i, cx in enumerate([1500, 2500], start=1):
    cut_opening(new_walls, cx - STD_WIN_W / 2, 8000, cx + STD_WIN_W / 2, 8000,
                WIN_SILL, WIN_SILL + STD_WIN_H, "W7_%d_Spalnya3_Okno" % i)

cut_opening(new_walls, 6000 - BIG_WIN_W / 2, 8000, 6000 + BIG_WIN_W / 2, 8000,
            WIN_SILL, WIN_SILL + BIG_WIN_H, "W8_Kuhnya_Zadnee_Bolshoe_Okno")
doc.recompute()

room_area_sum = sum(a for (_, a) in rooms) + 28.9  # + кухня-гостиная (считана отдельно)
print("\n--- Планировка ---")
print("Сумма площадей комнат (по факту нарезки, справочно): %.1f кв.м" % room_area_sum)
print("Большое окно спальни: %.0f x %.0f мм (пропорция 1:1.73)" % (BIG_WIN_W, BIG_WIN_H))
print("Стандартные окна кухни: %.0f x %.0f мм (пропорция 1:1.73)" % (STD_WIN_W, STD_WIN_H))

# =====================================================================
# ПРОВЕРКА СООТВЕТСТВИЯ РЕГЛАМЕНТУ ГПЗУ (ТЗ v2.0)
# =====================================================================

ridge_height_total = EAVE_HEIGHT + (NEW_HOUSE_WIDTH / 2.0) * math.tan(math.radians(ROOF_ANGLE_DEG))
footprint_area = NEW_HOUSE_LENGTH * NEW_HOUSE_WIDTH
gap_to_old_house = new_x0 - (ox0 + OLD_HOUSE_LENGTH) if NEW_HOUSE_DIRECTION >= 0 else ox0 - (new_x0 + NEW_HOUSE_LENGTH)

print("\n--- Проверка соответствия ГПЗУ / ТЗ v2.0 ---")
print("Длина уличного фасада: %.2f м (лимит <= 12 м) -> %s" %
      (NEW_HOUSE_LENGTH, "OK" if NEW_HOUSE_LENGTH <= 12.0 else "НАРУШЕНИЕ"))
print("Ширина дома: %.2f м (лимит <= 8 м) -> %s" %
      (NEW_HOUSE_WIDTH, "OK" if NEW_HOUSE_WIDTH <= 8.0 else "НАРУШЕНИЕ"))
print("Уклон кровли: %.1f° (диапазон 30-40°) -> %s" %
      (ROOF_ANGLE_DEG, "OK" if 30.0 <= ROOF_ANGLE_DEG <= 40.0 else "НАРУШЕНИЕ"))
print("Высота до конька (расчётная, от карниза): %.2f м (лимит <= 7.5 м) -> %s" %
      (ridge_height_total, "OK" if ridge_height_total <= 7.5 else "НАРУШЕНИЕ"))
print("Площадь пятна застройки (по внешнему контуру): %.1f кв.м (ориентир 90-110 кв.м жилой площади - для справки)" %
      footprint_area)
print("Зазор до существующего дома: %.2f м (требуется >= %.1f м) -> %s" %
      (gap_to_old_house, CONSTRUCTION_CLEARANCE, "OK" if gap_to_old_house >= CONSTRUCTION_CLEARANCE - 0.001 else "НАРУШЕНИЕ"))

doc.recompute()
doc.saveAs(OUTPUT_FILE)
print("\nМодель сохранена: %s" % OUTPUT_FILE)
