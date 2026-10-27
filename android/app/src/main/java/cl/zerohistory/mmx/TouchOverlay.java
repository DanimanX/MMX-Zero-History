// Capa táctil: dibuja el pad y traduce toques a una máscara de botones SNES.
//
// La geometría replica src/platform/android/x3_touch_controls.c: las teclas
// cuadradas se miden en unidades del lado corto, no en fracciones
// independientes de ancho y alto. Así siguen siendo cuadradas en 16:9,
// 19.5:9 y 20:9, y no se estiran cuando la ventana cambia de aspecto.
//
// La lógica de multi-touch (varios dedos, latcheo al deslizar, dos dedos en el
// mismo botón) vive en ese módulo C, que está probado en el escritorio con
// `bash tools/test_touch_controls.sh`. Esta clase dibuja, calcula los mismos
// rectángulos y reenvía.
//
// El envío al guest pasa por TouchBridge; ver el comentario en MainActivity
// sobre el punto de inyección que todavía falta en el host.

package cl.zerohistory.mmx;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.Build;
import android.view.DisplayCutout;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowInsets;

public class TouchOverlay extends View {
    // Bits, en el mismo orden que runner/src/keybinds.h.
    static final int BIT_R = 0, BIT_L = 1, BIT_X = 2, BIT_A = 3;
    static final int BIT_RIGHT = 4, BIT_LEFT = 5, BIT_DOWN = 6, BIT_UP = 7;
    static final int BIT_START = 8, BIT_SELECT = 9, BIT_Y = 10, BIT_B = 11;

    // Las mismas constantes que x3_touch_controls.c. Posiciones normalizadas
    // 0..1; tamaños en unidades del lado corto (alto).
    private static final float DPAD_CX = 0.155f;
    private static final float DPAD_CY = 0.760f;
    private static final float DPAD_ARM = 0.078f;
    private static final float DPAD_HALF = 0.070f;
    private static final float FACE_CX = 0.845f;
    private static final float FACE_CY = 0.760f;
    private static final float FACE_OFF = 0.085f;
    private static final float FACE_RAD = 0.056f;
    private static final float SHOULDER_W = 0.174f;
    private static final float SHOULDER_H = 0.070f;
    private static final float SHOULDER_Y = 0.578f;
    private static final float START_W = 0.192f;
    private static final float START_H = 0.062f;
    private static final float START_Y = 0.640f;
    private static final float SELECT_CY = 0.870f;
    private static final float SELECT_RAD = 0.045f;

    private static final class Key {
        final int bit;
        final float cx, cy;      // centro normalizado
        final float wUnits, hUnits;
        final String label;
        final int accent;
        Key(int bit, float cx, float cy, float wUnits, float hUnits,
            String label, int accent) {
            this.bit = bit;
            this.cx = cx;
            this.cy = cy;
            this.wUnits = wUnits;
            this.hUnits = hUnits;
            this.label = label;
            this.accent = accent;
        }
    }

    private final Key[] keys;
    private final RectF safe = new RectF();
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float opacity = 0.55f;
    private boolean mirrored;

    public TouchOverlay(Context context) {
        super(context);
        setFocusable(false);
        setClickable(false);

        fill.setStyle(Paint.Style.FILL);
        stroke.setStyle(Paint.Style.STROKE);
        stroke.setStrokeWidth(3f);
        fill.setColor(Color.argb((int) (opacity * 255), 20, 40, 60));
        label.setColor(Color.argb(230, 235, 245, 255));
        label.setTextAlign(Paint.Align.CENTER);

        final int cyan = Color.argb(210, 120, 235, 255);
        final int amber = Color.argb(225, 255, 190, 90);
        final int violet = Color.argb(210, 190, 160, 255);
        final int grey = Color.argb(200, 200, 210, 225);

        // Misma tabla que X3Touch_DefaultLayout().
        keys = new Key[]{
            square(BIT_UP, DPAD_CX, DPAD_CY - DPAD_ARM, DPAD_HALF, "▲", cyan),
            square(BIT_DOWN, DPAD_CX, DPAD_CY + DPAD_ARM, DPAD_HALF, "▼", cyan),
            square(BIT_LEFT, DPAD_CX - DPAD_ARM * 9f / 16f, DPAD_CY, DPAD_HALF, "<", cyan),
            square(BIT_RIGHT, DPAD_CX + DPAD_ARM * 9f / 16f, DPAD_CY, DPAD_HALF, ">", cyan),
            square(BIT_Y, FACE_CX, FACE_CY - FACE_OFF, FACE_RAD, "Y", amber),
            square(BIT_B, FACE_CX + FACE_OFF * 9f / 16f, FACE_CY, FACE_RAD, "B", amber),
            square(BIT_A, FACE_CX, FACE_CY + FACE_OFF, FACE_RAD, "A", amber),
            square(BIT_X, FACE_CX - FACE_OFF * 9f / 16f, FACE_CY, FACE_RAD, "X", amber),
            units(BIT_L, FACE_CX - FACE_OFF * 9f / 16f, SHOULDER_Y,
                  SHOULDER_W, SHOULDER_H, "L", violet),
            units(BIT_R, FACE_CX + FACE_OFF * 9f / 16f, SHOULDER_Y,
                  SHOULDER_W, SHOULDER_H, "R", violet),
            units(BIT_START, 0.5f, START_Y, START_W, START_H, "start", grey),
            square(BIT_SELECT, 0.5f, SELECT_CY, SELECT_RAD, "sel", grey),
        };
    }

    private static Key square(int bit, float cx, float cy, float half,
                              String text, int accent) {
        return new Key(bit, cx, cy, half * 2f, half * 2f, text, accent);
    }

    private static Key units(int bit, float cx, float cy, float wUnits,
                             float hUnits, String text, int accent) {
        return new Key(bit, cx, cy, wUnits, hUnits, text, accent);
    }

    /** Espeja la capa para jugadores zurdos (el módulo C hace lo mismo). */
    public void setMirrored(boolean mirrored) {
        this.mirrored = mirrored;
        invalidate();
    }

    public boolean isMirrored() {
        return mirrored;
    }

    public void setOpacity(float opacity) {
        this.opacity = Math.max(0.1f, Math.min(1f, opacity));
        fill.setColor(Color.argb((int) (this.opacity * 255), 20, 40, 60));
        invalidate();
    }

    @Override
    public WindowInsets onApplyWindowInsets(WindowInsets insets) {
        int left = insets.getSystemWindowInsetLeft();
        int top = insets.getSystemWindowInsetTop();
        int right = insets.getSystemWindowInsetRight();
        int bottom = insets.getSystemWindowInsetBottom();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            DisplayCutout cutout = insets.getDisplayCutout();
            if (cutout != null) {
                left = Math.max(left, cutout.getSafeInsetLeft());
                top = Math.max(top, cutout.getSafeInsetTop());
                right = Math.max(right, cutout.getSafeInsetRight());
                bottom = Math.max(bottom, cutout.getSafeInsetBottom());
            }
        }
        setPadding(left, top, right, bottom);
        updateSafeRect();
        return insets;
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        updateSafeRect();
    }

    private void updateSafeRect() {
        int l = getPaddingLeft();
        int t = getPaddingTop();
        int r = Math.max(l, getWidth() - getPaddingRight());
        int b = Math.max(t, getHeight() - getPaddingBottom());
        safe.set(l, t, r, b);
        if (!safe.isEmpty()) {
            // Keep the C tracker's hit boxes in step with the real surface.
            TouchBridge.nativeSetAspect(safe.width() / Math.max(1f, safe.height()));
        }
        invalidate();
    }

    private RectF rectFor(Key k) {
        float w = Math.max(1f, safe.width());
        float h = Math.max(1f, safe.height());
        float unit = Math.min(w, h);
        float cx = (mirrored ? 1f - k.cx : k.cx) * w;
        float bw = k.wUnits * unit;
        float bh = k.hUnits * unit;
        return new RectF(safe.left + cx - bw / 2f, safe.top + k.cy * h - bh / 2f,
                safe.left + cx + bw / 2f, safe.top + k.cy * h + bh / 2f);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (safe.isEmpty()) {
            safe.set(0, 0, getWidth(), getHeight());
        }
        for (Key k : keys) {
            RectF r = rectFor(k);
            float radius = Math.min(18f, Math.min(r.width(), r.height()) * 0.28f);
            fill.setColor(Color.argb((int) (opacity * 255), 20, 40, 60));
            stroke.setColor(k.accent);
            canvas.drawRoundRect(r, radius, radius, fill);
            canvas.drawRoundRect(r, radius, radius, stroke);

            label.setTextSize(Math.max(11f, Math.min(r.width(), r.height()) * 0.46f));
            label.setColor(Color.argb(240, 238, 244, 255));
            Paint.FontMetrics fm = label.getFontMetrics();
            float baseline = r.centerY() - (fm.ascent + fm.descent) / 2f;
            canvas.drawText(k.label, r.centerX(), baseline, label);
        }
    }

    private int bitsAt(float nx, float ny) {
        float w = Math.max(1f, safe.width());
        float h = Math.max(1f, safe.height());
        int bits = 0;
        for (Key k : keys) {
            RectF r = rectFor(k);
            float l = (r.left - safe.left) / w;
            float t = (r.top - safe.top) / h;
            float rr = (r.right - safe.left) / w;
            float bb = (r.bottom - safe.top) / h;
            if (nx >= l && nx <= rr && ny >= t && ny <= bb) {
                bits |= 1 << k.bit;
            }
        }
        return bits;
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (safe.isEmpty()) {
            safe.set(0, 0, Math.max(1f, getWidth()), Math.max(1f, getHeight()));
        }
        int action = event.getActionMasked();
        switch (action) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_POINTER_DOWN:
            case MotionEvent.ACTION_MOVE: {
                for (int i = 0; i < event.getPointerCount(); ++i) {
                    int id = event.getPointerId(i);
                    // Normalizado al área segura: es el mismo espacio que usa
                    // X3Touch_HitTest en el módulo C.
                    float nx = (event.getX(i) - safe.left)
                            / Math.max(1f, safe.width());
                    float ny = (event.getY(i) - safe.top)
                            / Math.max(1f, safe.height());
                    if (action == MotionEvent.ACTION_MOVE) {
                        TouchBridge.nativeMoveTouch(id, nx, ny);
                    } else {
                        TouchBridge.nativeDownTouch(id, nx, ny, bitsAt(nx, ny));
                    }
                }
                invalidate();
                return true;
            }
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_POINTER_UP:
            case MotionEvent.ACTION_CANCEL: {
                TouchBridge.nativeUpTouch(event.getPointerId(event.getActionIndex()));
                invalidate();
                if (action == MotionEvent.ACTION_CANCEL) {
                    releaseAll();
                    return true;
                }
                return true;
            }
            default:
                return super.onTouchEvent(event);
        }
    }

    public void releaseAll() {
        TouchBridge.nativeReleaseAll();
        invalidate();
    }
}
