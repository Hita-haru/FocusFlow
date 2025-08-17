# FocusFlow WebViewアプリ作成チュートリアル

このチュートリアルでは、現在開発しているWebアプリケーション「FocusFlow」を、AndroidのWebViewコンポーネントを使ってラッピングし、ネイティブアプリのように動作させる手順を解説します。

## はじめに

### 目的
Webサイトをそのまま表示するだけのシンプルなAndroidアプリを作成します。これにより、ユーザーはブラウザのアドレスバーなどを意識することなく、FocusFlowをあたかも専用アプリのように利用できます。

### 前提条件
*   ご自身のPCに[Android Studio](https://developer.android.com/studio)がインストールされていること。
*   FocusFlowのWebアプリケーションが、サーバー上で起動しており、スマートフォンからアクセス可能な状態であること。

---

## ステップ1: Android Studioで新規プロジェクトを作成

まず、アプリの器となるプロジェクトを作成します。

1.  Android Studioを起動し、「**New Project**」を選択します。
2.  「**Phone and Tablet**」タブで、「**Empty Views Activity**」を選択し、「Next」をクリックします。
3.  プロジェクトの設定画面で、以下のように入力します。
    *   **Name**: `FocusFlow` （アプリ名）
    *   **Package name**: `com.example.focusflow` （任意ですが、このままでOK）
    *   **Save location**: プロジェクトを保存したい場所を選択します。
    *   **Language**: `Kotlin` を選択します。
    *   **Minimum SDK**: `API 21: Android 5.0 (Lollipop)` を選択します。（多くの端末をサポートできます）
    *   **Build configuration**: `Groovy DSL` または `KTS` のどちらでも構いません。
4.  「**Finish**」をクリックします。プロジェクトの準備が始まるので、完了するまで少し待ちます。

---

## ステップ2: インターネット接続の許可を設定

アプリが外部のWebサイトにアクセスするためには、インターネット接続の許可をアプリに与える必要があります。

1.  左側のプロジェクトビューで、`app` -> `manifests` -> `AndroidManifest.xml` をダブルクリックして開きます。
2.  `<application>`タグの**直前**に、以下の1行をコピー＆ペーストしてください。

```xml
<!-- AndroidManifest.xml -->

<manifest ...>

    <!-- ★この行を追加 -->
    <uses-permission android:name="android.permission.INTERNET" />

    <application ...>
        ...
    </application>

</manifest>
```

---

## ステップ3: 画面レイアウトの修正

アプリの画面に、Webページを表示するための`WebView`を配置します。

1.  プロジェクトビューで、`app` -> `res` -> `layout` -> `activity_main.xml` をダブルクリックして開きます。
2.  デフォルトで配置されている`TextView`は不要なので削除します。ファイルの内容を、以下のコードですべて上書きしてください。

```xml
<!-- activity_main.xml -->

<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    tools:context=".MainActivity">

    <WebView
        android:id="@+id/webView"
        android:layout_width="0dp"
        android:layout_height="0dp"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

---

## ステップ4: プログラム本体(MainActivity)の記述

いよいよ、WebViewを動作させるためのKotlinコードを記述します。このコードがアプリの心臓部です。

1.  プロジェクトビューで、`app` -> `java` -> `com.example.focusflow` -> `MainActivity` をダブルクリックして開きます。
2.  ファイルの内容を、以下のコードですべて上書きしてください。

```kotlin
// MainActivity.kt

package com.example.focusflow

import android.annotation.SuppressLint
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)

        // --- WebViewの初期設定 ---

        // 1. JavaScriptを有効にする (多くのモダンなWebサイトで必須)
        webView.settings.javaScriptEnabled = true

        // 2. リンクを外部ブラウザではなくWebView内で開くようにする
        webView.webViewClient = WebViewClient()

        // 3. 表示したいWebアプリケーションのURLを読み込む
        // ★★★ 必ず、あなたのサーバーのIPアドレスまたはドメイン名に書き換えてください ★★★
        webView.loadUrl("http://YOUR_SERVER_IP_OR_DOMAIN")
    }

    // スマートフォンの「戻る」ボタンが押された時の処理
    override fun onBackPressed() {
        // もしWebView内で前のページに戻れるなら、戻る
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            // そうでなければ、通常の「戻る」ボタンの動作（アプリを閉じるなど）
            super.onBackPressed()
        }
    }
}

```

**【最重要】**
上記のコード内の`"http://YOUR_SERVER_IP_OR_DOMAIN"`の部分は、**必ずあなたのFocusFlowが動作しているサーバーのURLに書き換えてください。**

---

## ステップ5: アプリのビルドと実行

すべての設定が完了しました。

1.  Android Studioの上部にあるツールバーで、実行先のデバイス（エミュレータまたはUSBで接続した実機）を選択します。
2.  緑色の「再生」ボタン（`Run 'app'`）をクリックします。

ビルドが成功すれば、指定したデバイスでFocusFlowのWebサイトが表示されるアプリが起動します。

## まとめ

お疲れ様でした！この手順で、Web技術の知識だけでも、Webサイトをネイティブアプリのように見せかけることができました。ここからさらに、スプラッシュ画面を追加したり、ローディング表示を工夫したりすることで、よりアプリらしい体験を追求することも可能です。
