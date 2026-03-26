import numpy as np
 
class GCodeGenerator:
    """Generate CNC G-code for basic 2.5D operations."""
    
    def __init__(self, feed_rate=200, plunge_rate=50,
                 spindle_speed=8000, safe_z=5.0, tool_dia=6.0):
        self.feed = feed_rate       # mm/min
        self.plunge = plunge_rate   # mm/min (Z direction)
        self.spindle = spindle_speed  # RPM
        self.safe_z = safe_z        # mm
        self.tool_dia = tool_dia    # mm
        self.lines = []
        self.toolpath = []  # For visualization: list of (x,y,z)
    
    def header(self, program_name="PART001"):
        self.lines = [
            f"(Program: {program_name})",
            f"(Tool: D{self.tool_dia:.1f}mm endmill)",
            f"(Feed: {self.feed} mm/min, Spindle: {self.spindle} RPM)",
            "G90 G21 (Absolute, metric)",
            "G17 (XY plane)",
            f"G0 Z{self.safe_z:.1f} (Retract to safe height)",
            f"M3 S{self.spindle} (Spindle ON clockwise)",
            "G4 P2 (Dwell 2s for spindle to reach speed)",
        ]
    
    def footer(self):
        self.lines.extend([
            f"G0 Z{self.safe_z:.1f} (Retract)",
            "M5 (Spindle OFF)",
            "G0 X0 Y0 (Return to home)",
            "M30 (Program end)",
        ])
    
    def rapid_move(self, x=None, y=None, z=None):
        parts = ["G0"]
        if x is not None: parts.append(f"X{x:.3f}")
        if y is not None: parts.append(f"Y{y:.3f}")
        if z is not None: parts.append(f"Z{z:.3f}")
        self.lines.append(" ".join(parts))
        self._track(x, y, z)
    
    def linear_move(self, x=None, y=None, z=None, feed=None):
        f = feed or self.feed
        parts = ["G1"]
        if x is not None: parts.append(f"X{x:.3f}")
        if y is not None: parts.append(f"Y{y:.3f}")
        if z is not None: parts.append(f"Z{z:.3f}")
        parts.append(f"F{f}")
        self.lines.append(" ".join(parts))
        self._track(x, y, z)
    
    def _track(self, x, y, z):
        lx = self.toolpath[-1][0] if self.toolpath else 0
        ly = self.toolpath[-1][1] if self.toolpath else 0
        lz = self.toolpath[-1][2] if self.toolpath else self.safe_z
        self.toolpath.append((x if x else lx, y if y else ly,
                              z if z else lz))
    
    def rectangular_pocket(self, x, y, width, height, depth,
                            step_down=1.0, step_over=None):
        """Mill a rectangular pocket with zigzag toolpath."""
        if step_over is None:
            step_over = self.tool_dia * 0.6
        
        r = self.tool_dia / 2
        self.lines.append(f"(Pocket: {width}x{height}x{depth}mm "
                          f"at X{x} Y{y})")
        
        n_passes = int(np.ceil(depth / step_down))
        
        for p in range(n_passes):
            z = -min((p + 1) * step_down, depth)
            self.rapid_move(x + r, y + r)
            self.linear_move(z=z, feed=self.plunge)
            
            # Zigzag passes
            cx = x + r
            direction = 1
            while cx < x + width - r:
                if direction == 1:
                    self.linear_move(x=cx, y=y + height - r)
                else:
                    self.linear_move(x=cx, y=y + r)
                cx = min(cx + step_over, x + width - r)
                self.linear_move(x=cx)
                direction *= -1
            
            # Final pass
            if direction == 1:
                self.linear_move(x=cx, y=y + height - r)
            else:
                self.linear_move(x=cx, y=y + r)
            
            self.rapid_move(z=self.safe_z)
    
    def circular_pocket(self, cx, cy, diameter, depth,
                         step_down=1.0):
        """Mill a circular pocket with spiral toolpath."""
        r = diameter / 2
        tr = self.tool_dia / 2
        self.lines.append(f"(Circle: D{diameter}mm, "
                          f"depth {depth}mm at X{cx} Y{cy})")
        
        n_passes = int(np.ceil(depth / step_down))
        
        for p in range(n_passes):
            z = -min((p + 1) * step_down, depth)
            self.rapid_move(cx, cy)
            self.linear_move(z=z, feed=self.plunge)
            
            # Spiral outward
            current_r = tr
            while current_r < r - tr:
                n_pts = max(12, int(current_r * 2))
                for i in range(n_pts + 1):
                    angle = 2 * np.pi * i / n_pts
                    px = cx + current_r * np.cos(angle)
                    py = cy + current_r * np.sin(angle)
                    self.linear_move(px, py)
                current_r += self.tool_dia * 0.4
            
            # Final circle at full radius
            for i in range(25):
                angle = 2 * np.pi * i / 24
                px = cx + (r - tr) * np.cos(angle)
                py = cy + (r - tr) * np.sin(angle)
                self.linear_move(px, py)
            
            self.rapid_move(z=self.safe_z)
    
    def hole_pattern(self, centers, depth, peck_depth=2.0):
        """Drill holes at given centers using peck drilling."""
        self.lines.append(f"(Drilling: {len(centers)} holes, "
                          f"depth {depth}mm)")
        for i, (hx, hy) in enumerate(centers):
            self.rapid_move(hx, hy)
            self.rapid_move(z=1.0)
            
            current_z = 0
            while current_z > -depth:
                current_z = max(current_z - peck_depth, -depth)
                self.linear_move(z=current_z, feed=self.plunge)
                self.rapid_move(z=1.0)  # Retract for chip clear
            
            self.rapid_move(z=self.safe_z)
    
    def get_gcode(self):
        return "\n".join(self.lines)
 
if __name__ == "__main__":
    gen = GCodeGenerator(feed_rate=200, spindle_speed=8000,
                          tool_dia=6.0)
    gen.header("TEST_PART")
    gen.rectangular_pocket(10, 10, 40, 30, 5, step_down=1.5)
    gen.circular_pocket(80, 40, 20, 3)
    gen.hole_pattern([(20,50),(40,50),(60,50),(80,50)], depth=8)
    gen.footer()
    
    gcode = gen.get_gcode()
    with open("test_part.nc", "w") as f:
        f.write(gcode)
    print(f"Generated {len(gen.lines)} lines of G-code")
    print(f"Toolpath points: {len(gen.toolpath)}")
    print(f"Saved to test_part.nc")
    print(f"\nFirst 10 lines:")
    for line in gen.lines[:10]:
        print(f"  {line}")
