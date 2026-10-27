// Capa táctil: dibuja el pad y traduce toques a una máscara de botones SNES.
//
// La geometría replica src/platform/android/x3_touch_controls.c. La lógica de
// multi-touch (varios dedos, latcheo al deslizar, dos dedos en el mismo botón)
// vive en ese módulo C, que está probado en el escritorio con
// `bash tools/test_touch_controls.sh`. Esta clase solo dibuja y reenvía.
//
// El envío al guest pasa por TouchBridge.nativeSetTouch(); ver el comentario en
// MainActivity sobre el punto de inyección que todavía falta en el host.

package cl.zerohistory.mmx;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;

public class TouchOverlay extends View {
    // Bits, en el mismo orden que runner/src/keybinds.h.
    static final int BIT_R = 0, BIT_L = 1, BIT_X = 2, BIT_A = 3;
    static final int BIT_RIGHT = 4, BIT_LEFT = 5, BIT_DOWN = 6, BIT_UP = 7;
    static final int BIT_START = 8, BIT_SELECT = 9, BIT_Y = 10, BIT_B = 11;

    private static final class Key {
        final RectF rect = new RectF(); // normalizado 0..1
        final int bit;
        Key(int bit) { this.bit = bit; }
    }

    private final Key[] keys;
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float opacity = 0.55f;

    public TouchOverlay(Context context) {
        super(context);
        setFocusable(false);
        setClickable(false);

        fill.setStyle(Paint.Style.FILL);
        stroke.setStyle(Paint.Style.STROKE);
        stroke.setStrokeWidth(3f);
        stroke.setColor(Color.argb(210, 120, 235, 255));
        fill.setColor(Color.argb((int) (opacity * 255), 20, 40, 60));
        label.setColor(Color.argb(230, 235, 245, 255));
        label.setTextSize(34f);
        label.setTextAlign(Paint.Align.CENTER);

        // D-pad abajo-izquierda.
        keys = new Key[]{
            centre(BIT_UP, 0.155f, 0.682f, 0.070f),
            centre(BIT_DOWN, 0.155f, 0.838f, 0.070f),
            centre(BIT_LEFT, 0.077f, 0.760f, 0.070f),
            centre(BIT_RIGHT, 0.233f, 0.760f, 0.070f),
            // Cuatro botones SNES en rombo.
            centre(BIT_Y, 0.845f, 0.675f, 0.056f),
            centre(BIT_B, 0.930f, 0.760f, 0.056f),
            centre(BIT_A, 0.845f, 0.845f, 0.056f),
            centre(BIT_X, 0.760f, 0.760f, 0.056f),
            // Hombros.
            box(BIT_L, 0.711f, 0.543f, 0.098f, 0.070f),
            box(BIT_R, 0.881f, 0.543f, 0.098f, 0.070f),
            // start y select.
            box(BIT_START, 0.446f, 0.609f, 0.108f, 0.062f),
            centre(BIT_SELECT, 0.500f, 0.870f, 0.045f),
        };
    }

    private static Key centre(int bit, float cx, float cy, float half) {
        Key k = new Key(bit);
        k.rect.set(cx - half, cy - half, cx + half, cy + half);
        return k;
    }

    private static Key box(int bit, float x, float y, float w, float h) {
        Key k = new Key(bit);
        k.rect.set(x, y, x + w, y + h);
        return k;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float w = getWidth();
        float h = getHeight();
        for (Key k : keys) {
            RectF r = new RectF(k.rect.left * w, k.rect.top * h,
                    k.rect.right * w, k.rect.bottom * h);
            canvas.drawRoundRect(r, 14f, 14f, fill);
            canvas.drawRoundRect(r, 14f, 14f, stroke);
        }
    }

    private int bitsAt(float nx, float ny) {
        int bits = 0;
        for (Key k : keys) {
            if (nx >= k.rect.left && nx <= k.rect.right
                    && ny >= k.rect.top && ny <= k.rect.bottom) {
                bits |= 1 << k.bit;
            }
        }
        return bits;
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        float w = Math.max(1f, getWidth());
        float h = Math.max(1f, getHeight());
        int action = event.getActionMasked();
        switch (action) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_POINTER_DOWN:
            case MotionEvent.ACTION_MOVE: {
                for (int i = 0; i < event.getPointerCount(); ++i) {
                    int id = event.getPointerId(i);
                    float nx = event.getX(i) / w;
                    float ny = event.getY(i) / h;
                    if (action == MotionEvent.ACTION_MOVE) {
                        TouchBridge.nativeMoveTouch(id, nx, ny);
                    } else {
                        TouchBridge.nativeDownTouch(id, nx, ny, bitsAt(nx, ny));
                    }
                }
                return true;
            }
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_POINTER_UP:
            case MotionEvent.ACTION_CANCEL: {
                TouchBridge.nativeUpTouch(event.getPointerId(event.getActionIndex()));
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
