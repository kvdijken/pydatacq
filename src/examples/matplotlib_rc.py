import matplotlib.pyplot as plt
import matplotlib as mpl

dpi = 100 #decided by display device

default_text_size_points = 10
default_line_width_points = 1

# matplotlib rules
mpl_points_per_inch = 72
mpl_pixels_per_point = dpi / mpl_points_per_inch

line_width_pixels = 1
line_width_points = line_width_pixels / mpl_pixels_per_point
plt.rcParams['lines.linewidth'] = line_width_points / 2
_lw = line_width_points

text_size_points = default_text_size_points
plt.rcParams['font.size'] = text_size_points

plt.rcParams['figure.dpi'] = dpi
mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=['green'],alpha=[0.66])

plt.rcParams['toolbar'] = 'None'
plt.rcParams['axes.xmargin'] = 0

