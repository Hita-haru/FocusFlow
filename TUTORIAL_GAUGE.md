# FocusFlow開発チュートリアル - フォーカスゲージ編

このチュートリアルでは、「フォーカスモード」のページに、AIを使わない簡易的な「フォーカスゲージ」を実装する方法を解説します。

## 1. コンセプト：なぜこの方法なのか？

ブラウザで動作するWebアプリケーションは、OS上の他のアプリを監視したり、PCのスリープを直接検知したりすることができません。この制約の中で、意味のあるフォーカスゲージを作るために、以下の2つの技術を組み合わせます。

1.  **時刻ベースのタイマー（スリープ対応）**: タイマーの残り時間を「未来の終了時刻 - 現在時刻」で計算することで、PCがスリープしても復帰時に正しい残り時間を表示します。
2.  **Page Visibility API（寄り道検知）**: ユーザーがページを表示しているか、別のタブに切り替えたかを検知します。これにより「意図しないスリープ」と「意図的なタブ移動」を区別します。

## 2. Step 1: ゲージのUI要素を追加する

まず、`app/templates/focus.html`にゲージ本体となるHTML要素を追加し、スタイルを定義します。

### HTMLの追加
`timer-display`の下に、ゲージのコンテナとバーを追加します。

```html
<!-- focus.html の timer-display の下に追加 -->
<div id="gauge-container">
    <div id="gauge-bar"></div>
</div>
```

### CSSの追加
`<style>`ブロック内に、ゲージ用のCSSを追加します。

```css
/* focus.html の <style> 内に追加 */
#gauge-container {
    width: 80%;
    max-width: 600px;
    height: 20px;
    background-color: #3a3a3c;
    border-radius: 10px;
    margin-top: 1.5rem;
    overflow: hidden;
}

#gauge-bar {
    width: 100%;
    height: 100%;
    background-color: var(--primary-color);
    border-radius: 10px;
    transition: width 0.3s ease-in-out, background-color 0.5s;
}
```

## 3. Step 2: JavaScriptロジックの全体像

次に、`focus.html`の`<script>`ブロックを、ゲージを制御するロジックを含んだ以下の完成版コードに置き換えます。主な変更点にはコメントで解説を加えています。

```javascript
// focus.html の <script>ブロック全体を以下に置き換える

document.addEventListener('DOMContentLoaded', () => {
    // --- 定数と要素の定義 ---
    const FOCUS_TIME_SECONDS = 25 * 60;
    const BREAK_TIME_SECONDS = 5 * 60;
    const taskName = "{{ task_name|escape }}";

    const elements = {
        // ... (既存の要素定義は変更なし)
        gaugeBar: document.getElementById('gauge-bar') // ゲージバーを新たに追加
    };

    const sound = { /* ... */ };

    // --- 状態管理オブジェクト ---
    let state = {
        timerId: null,
        mode: 'FOCUS',
        targetTime: 0,
        totalAccumulatedFocusTime: 0,
        currentPhaseStartTime: 0,
        gaugeLevel: 100, // ゲージレベル(0-100)を新たに追加
        lastHiddenTime: 0 // ページが非表示になった時刻を記録
    };

    // --- イベントリスナーの登録 ---
    elements.endSessionBtn.addEventListener('click', endSession);
    // Page Visibility APIのイベントリスナーを新たに追加
    document.addEventListener('visibilitychange', handleVisibilityChange);


    // --- 主要関数 ---

    function endSession() { /* ... (変更なし) */ }
    function logSession(duration) { /* ... (変更なし) */ }

    // ★【新規】可視性変更のハンドラ
    function handleVisibilityChange() {
        if (document.hidden) {
            // ページが非表示になったら、その時刻を記録
            state.lastHiddenTime = Date.now();
        } else {
            // ページが再表示されたら、非表示だった時間を計算
            const hiddenDuration = Date.now() - state.lastHiddenTime;
            
            // 非表示時間が2分以上ならスリープとみなし、ペナルティなし
            if (hiddenDuration > 120000) { // 2分 = 120,000ミリ秒
                // 何もしない（ゲージはそのまま）
            } else {
                // 2分未満ならタブ移動とみなし、ペナルティを課す
                // ここではシンプルにゲージを0にする
                state.gaugeLevel = 0;
            }
        }
    }

    // ★【更新】表示更新関数
    function updateDisplay() {
        const now = Date.now();
        const timeLeft = Math.round((state.targetTime - now) / 1000);
        
        if (timeLeft >= 0) {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            elements.timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }

        let currentFocusTime = state.totalAccumulatedFocusTime;
        if (state.mode === 'FOCUS') {
            currentFocusTime += (now - state.currentPhaseStartTime);
        }
        const accumulatedMinutes = Math.floor(currentFocusTime / 1000 / 60);
        elements.accumulatedTimeDisplay.textContent = `合計フォーカス時間: ${accumulatedMinutes}分`;

        // ゲージのUIを更新
        elements.gaugeBar.style.width = `${state.gaugeLevel}%`;
    }

    function startPhase(mode) { /* ... (変更なし) */ }

    // ★【更新】毎秒実行されるtick関数
    function tick() {
        if (Date.now() >= state.targetTime) {
            startPhase(state.mode === 'FOCUS' ? 'BREAK' : 'FOCUS');
        }

        // ページが表示されている、かつフォーカスモードの時だけゲージを回復
        if (!document.hidden && state.mode === 'FOCUS') {
            state.gaugeLevel = Math.min(100, state.gaugeLevel + 0.2); // 少しずつ回復
        }

        updateDisplay();
    }

    function init() {
        // ... (既存の初期化処理)
        state.timerId = setInterval(tick, 1000);
        tick();
    }

    init();
});
```

## 4. まとめ

お疲れ様でした！以上の変更により、フォーカスゲージは以下の賢い挙動を手に入れました。

*   **フォーカス中:** ゲージは100%を維持、またはゆっくりと回復します。
*   **タブを切り替えた時:** ゲージが即座に0%になり、ペナルティを受けます。
*   **PCがスリープした時:** ゲージは減りません。復帰後、中断した時点から再開します。
*   **タイマー:** スリープ中も時間は正確にカウントされ続けます。

これにより、ブラウザの制約内で可能な限りインテリジェントなフォーカスゲージが完成しました。
