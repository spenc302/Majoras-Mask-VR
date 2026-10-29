package com.fulldivegames.majorasmaskvr;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.RemoteException;
import android.os.ResultReceiver;
import android.os.SystemClock;
import android.widget.TextView;

import java.util.concurrent.atomic.AtomicBoolean;

/** Lives outside SDL's process. Never kills the game or starts a second native engine. */
public final class StateRestartActivity extends Activity {
    static final String READY = "mmvr.restart.ready";
    static final String OWNER = "mmvr.restart.owner";
    static final String COMMIT = "mmvr.restart.commit";

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean ownerDied = new AtomicBoolean(false);

    private StateRestartPolicy policy;
    private IBinder owner;
    private TextView status;

    private final Runnable poll = this::check;

    private final IBinder.DeathRecipient ownerDeathRecipient = () -> {
        ownerDied.set(true);

        android.util.Log.i(
                "MMVR-Lifecycle",
                "[MMVR-Lifecycle] Binder death callback received"
        );

        // Binder callbacks can arrive on a Binder thread. All policy and
        // Activity work remains on the helper's main thread.
        handler.post(this::check);
    };

    @Override
    public void onCreate(Bundle saved) {
        super.onCreate(saved);

        android.util.Log.i(
                "MMVR-Lifecycle",
                "[MMVR-Lifecycle] StateRestartActivity.onCreate()"
        );

        status = new TextView(this);
        status.setTextSize(24);
        status.setPadding(48, 48, 48, 48);
        status.setText("Restarting to restore saved settings...");
        setContentView(status);

        Bundle request = getIntent().getExtras();
        owner = request == null ? null : request.getBinder(OWNER);

        ResultReceiver ready =
                request == null ? null : request.getParcelable(READY);

        if (owner == null || ready == null) {
            fail("Restart request expired. Open the game again manually.");
            return;
        }

        policy = new StateRestartPolicy(SystemClock.elapsedRealtime());

        // Register before acknowledging the request. If the Binder has
        // already died, linkToDeath throws RemoteException; record that
        // condition and let the normal commit policy decide what happens.
        try {
            owner.linkToDeath(ownerDeathRecipient, 0);

            android.util.Log.i(
                    "MMVR-Lifecycle",
                    "[MMVR-Lifecycle] Binder death recipient registered"
            );

            // Cover a death that raced with registration/checking.
            if (!owner.isBinderAlive()) {
                ownerDied.set(true);

                android.util.Log.i(
                        "MMVR-Lifecycle",
                        "[MMVR-Lifecycle] Binder already dead after registration"
                );
            }
        } catch (RemoteException deadBinder) {
            ownerDied.set(true);

            android.util.Log.i(
                    "MMVR-Lifecycle",
                    "[MMVR-Lifecycle] Binder already dead during registration",
                    deadBinder
            );
        }

        android.util.Log.i(
                "MMVR-Lifecycle",
                "[MMVR-Lifecycle] Sending COMMIT receiver to game"
        );

        ResultReceiver commit = new ResultReceiver(handler) {
            @Override
            protected void onReceiveResult(int code, Bundle data) {
                if (policy == null || isFinishing()) {
                    return;
                }

                if (code == Activity.RESULT_OK) {
                    boolean accepted =
                            policy.commit(SystemClock.elapsedRealtime());

                    android.util.Log.i(
                            "MMVR-Lifecycle",
                            "[MMVR-Lifecycle] Commit received; accepted="
                                    + accepted
                    );
                } else {
                    policy.cancel();

                    android.util.Log.i(
                            "MMVR-Lifecycle",
                            "[MMVR-Lifecycle] Restart cancelled by game"
                    );
                }

                check();
            }
        };

        Bundle response = new Bundle();
        response.putParcelable(COMMIT, commit);
        ready.send(Activity.RESULT_OK, response);

        check();
    }

    private boolean isOwnerAlive() {
        if (ownerDied.get() || owner == null) {
            return false;
        }

        boolean alive = owner.isBinderAlive();

        if (!alive) {
            ownerDied.set(true);
        }

        return alive;
    }

    private void check() {
        if (isFinishing() || policy == null) {
            return;
        }

        handler.removeCallbacks(poll);

        boolean ownerAlive = isOwnerAlive();

        switch (policy.poll(
                SystemClock.elapsedRealtime(),
                ownerAlive
        )) {
            case WAIT:
                handler.postDelayed(poll, 100);
                break;

            case LAUNCH:
                android.util.Log.i(
                        "MMVR-Lifecycle",
                        "[MMVR-Lifecycle] Original process death confirmed; "
                                + "attempting SetupActivity launch"
                );

                try {
                    startActivity(
                            new Intent(this, SetupActivity.class)
                                    .addFlags(
                                            Intent.FLAG_ACTIVITY_NEW_TASK
                                                    | Intent.FLAG_ACTIVITY_CLEAR_TASK
                                    )
                    );

                    android.util.Log.i(
                            "MMVR-Lifecycle",
                            "[MMVR-Lifecycle] SetupActivity startActivity returned"
                    );

                    finish();
                } catch (RuntimeException failure) {
                    android.util.Log.e(
                            "MMVR-Lifecycle",
                            "[MMVR-Lifecycle] SetupActivity launch failed",
                            failure
                    );

                    fail(
                            "Automatic restart failed. "
                                    + "Open the game again manually."
                    );
                }
                break;

            case STOP:
                if (isOwnerAlive()) {
                    android.util.Log.w(
                            "MMVR-Lifecycle",
                            "[MMVR-Lifecycle] Restart timed out or was cancelled; "
                                    + "original process remains alive"
                    );

                    finish();
                } else {
                    fail(
                            "Restart request expired. "
                                    + "Open the game again manually."
                    );
                }
                break;
        }
    }

    private void fail(String message) {
        handler.removeCallbacks(poll);

        if (status != null) {
            status.setText(message);
        }

        android.util.Log.w("MMVR-Lifecycle", message);
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(poll);

        if (owner != null) {
            try {
                owner.unlinkToDeath(ownerDeathRecipient, 0);
            } catch (RuntimeException ignored) {
                // The Binder may already be dead or unlinked.
            }
        }

        super.onDestroy();
    }
}
