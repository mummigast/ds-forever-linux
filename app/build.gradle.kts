import java.util.Properties
import java.io.FileInputStream

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.dagger.hilt)
    alias(libs.plugins.jetbrains.kotlin.android)
    alias(libs.plugins.jetbrains.serialization)
    alias(libs.plugins.kotlinter)
    alias(libs.plugins.ksp)
}

val keystorePropertiesFile = rootProject.file("app/keystores/keystore.properties")
val keystoreProperties: Properties? = if (keystorePropertiesFile.exists()) {
    Properties().apply {
        load(FileInputStream(keystorePropertiesFile))
    }
} else null

// Linux Streaming Edition: what a streaming-only build leaves out (see FORK.md "What is left out")
val localRuntime = (findProperty("localRuntime") as String?)?.toBoolean() ?: false
val STREAM_ONLY_DROPPED_LIBS = listOf("libkgslshim.so", "libpulse.so", "libpulsecommon-13.0.so", "libpulsecore-13.0.so", "libsndfile.so",
    "libltdl.so", "liblsfg-vk-layer.so", "libgnoverlay.so", "libgamenative_dns_v4mapped.so", "libevshim.so").map { "**/$it" }
val STREAM_ONLY_DROPPED_ASSETS = listOf("<dir>bundled_components", "<dir>box86_64", "<dir>wowbox64", "<dir>wincomponents", "<dir>lsfg_vk",
    "pulseaudio-gamenative-*.tzst", "redirect.tzst").map { "!$it" }

android {
    namespace = "app.gamenative"
    compileSdk = 36

    // https://developer.android.com/ndk/downloads
    ndkVersion = "27.2.12479018"

    signingConfigs {
        // the DS Forever key: WC_KEYSTORE / WC_KEYSTORE_PASS / WC_KEY_ALIAS / WC_KEY_PASS from the environment (the user's own
        // Gradle properties, handed over by the build wrapper). Never in this repo. Without them the build is debug-signed.
        create("dsforever") {
            System.getenv("WC_KEYSTORE")?.let { ks ->
                storeFile = file(ks)
                storePassword = System.getenv("WC_KEYSTORE_PASS")
                keyAlias = System.getenv("WC_KEY_ALIAS")
                keyPassword = System.getenv("WC_KEY_PASS")
            }
        }
        create("release") {
            if (keystoreProperties != null) {
                storeFile = file(keystoreProperties["storeFile"].toString())
                storePassword = keystoreProperties["storePassword"].toString()
                keyAlias = keystoreProperties["keyAlias"].toString()
                keyPassword = keystoreProperties["keyPassword"].toString()
            }
        }
    }

    defaultConfig {
        // DS Forever (S5, the user 2026-10-08: "(a) Become 'DS Forever'"): THE one app, installed over the old DS Forever app
        applicationId = "app.dsforever.companion.linux"  // Linux Edition: installs beside the official app

        minSdk = 26

        manifestPlaceholders["screenOrientation"] = "unspecified"
        buildConfigField("boolean", "XR_BUILD", "false")

        versionCode = 1482
        versionName = "1.0.33"

        buildConfigField("boolean", "GOLD", "false")
        // DS Forever's self-update (Track C, the user's rulings 2026-10-12): the PUBLIC release repo "owner/repo" whose latest GitHub
        // release carries DS-Forever-<version>.apk. Empty = no repo yet: the update check says so and does nothing. No token, ever.
        buildConfigField("String", "DSF_RELEASE_REPO", "\"mummigast/ds-forever-linux\"")
        val iconValue = "@mipmap/ic_launcher"
        val iconRoundValue = "@mipmap/ic_launcher_round"
        manifestPlaceholders.putAll(
            mapOf(
                "icon" to iconValue,
                "roundIcon" to iconRoundValue,
            ),
        )

        ndk {
            //abiFilters.addAll(listOf("arm64-v8a", "armeabi-v7a"))
        }

        // Localization support - specify which languages to include
        resourceConfigurations += listOf(
            "en",      // English (default)
            "es",      // Spanish
            "da",      // Danish
            "pt-rBR",  // Portuguese (Brazilian)
            "zh-rTW",  // Traditional Chinese
            "zh-rCN",  // Simplified Chinese
            "fr",      // French
            "de",      // German
            "uk",      // Ukrainian
            "it",      // Italian
            "ro",      // Română
            "pl",      // Polish
            "ru",      // Russian
            "ko",      // Korean
            "ja",      // Japanese
            // TODO: Add more languages here using the ISO 639-1 locale code with regional qualifiers (e.g., "pt-rPT" for European Portuguese)
        )

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }

        proguardFiles(
            // getDefaultProguardFile("proguard-android-optimize.txt"),
            getDefaultProguardFile("proguard-android.txt"),
            "proguard-rules.pro",
        )
    }

    flavorDimensions += "androidApi"
    productFlavors {
        create("modern") {
            dimension = "androidApi"
            minSdk = 29
            targetSdk = 36
            ndk.abiFilters += listOf("arm64-v8a")
            buildConfigField("boolean", "MODERN_ANDROID", "true")
            buildConfigField("String", "PRELOAD_BIONIC_SO", "\"libredirect-bionic-wx.so\"")
        }
    }

    buildTypes {
        debug {
            isDebuggable = true
            isMinifyEnabled = false
            isShrinkResources = false
            signingConfig = signingConfigs.getByName(if (System.getenv("WC_KEYSTORE") != null) "dsforever" else "debug")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = signingConfigs.getByName("dsforever")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/DebugProbesKt.bin"
            excludes += "/junit/runner/smalllogo.gif"
            excludes += "/junit/runner/logo.gif"
            excludes += "/META-INF/versions/9/OSGI-INF/MANIFEST.MF"
        }
        jniLibs {
            // 'extractNativeLibs' was not enough to keep the jniLibs and
            // the libs went missing after adding on-demand feature delivery
            useLegacyPackaging = true
            // Linux Streaming Edition (2026-11-17): the local game container's prebuilt runtime is left out (streaming never runs it;
            // these are also the inputs RELEASE_NOTICES.md lists as not cleared for redistribution). -PlocalRuntime=true keeps them.
            if (!localRuntime) excludes += STREAM_ONLY_DROPPED_LIBS
        }
    }
    // Linux Streaming Edition: the container's assets (Proton/DXVK/Turnip, box64, PulseAudio, redirect, Windows components, LSFG)
    if (!localRuntime) androidResources { ignoreAssetsPatterns += STREAM_ONLY_DROPPED_ASSETS }
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            all {
                it.maxHeapSize = "4g"
                it.testLogging { events("started", "failed") }
            }
        }
    }

    lint {
        // Locale files ship full AndroidX appcompat (abc_*) translations that aren't in the
        // default locale. These extra translations are harmless and pre-existing; without this
        // the release-only lintVital pass fails on 150+ ExtraTranslation errors.
        disable += "ExtraTranslation"
    }

    // Configure Assets to be used in different variants
    sourceSets {
        getByName("modern") {
            assets {
                srcDirs("src/modern/assets", "src/main/assets")
            }
        }
    }

    kotlinter {
        ignoreFormatFailures  = false
    }

}

tasks.configureEach {
    if (name == "preModernReleaseBuild") {
        doFirst {
            require(listOf("WC_KEYSTORE", "WC_KEYSTORE_PASS", "WC_KEY_ALIAS", "WC_KEY_PASS").all {
                !System.getenv(it).isNullOrBlank()
            }) { "Release signing needs all four WC_KEY* environment values; use modernDebug for development" }
        }
    }
}

dependencies {
    implementation(project(":dsforever"))   // DS Forever fork
    implementation(libs.okhttp)

    // Winlator
    implementation(libs.bundles.winlator)
    implementation(libs.zstd.jni) { artifact { type = "aar" } }
    implementation(libs.xz)

    // Jetpack Compose
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.bundles.compose)
    debugImplementation(libs.androidx.ui.tooling)

    // Support
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.datastore.preferences)
    implementation(libs.jetbrains.kotlinx.json)
    implementation(libs.kotlin.coroutines)
    implementation(libs.timber)

    // Hilt
    implementation(libs.bundles.hilt)

    // KSP (Hilt)
    ksp(libs.bundles.ksp)


    // Memory Leak Detection
    // debugImplementation("com.squareup.leakcanary:leakcanary-android:3.0-alpha-8")

    // Testing
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.runner)
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.test.manifest)
    testImplementation(libs.junit)
    testImplementation(libs.robolectric)
    testImplementation(libs.mockito.core)
    testImplementation(libs.mockito.kotlin)
    testImplementation(libs.mockk)
    testImplementation(libs.androidx.ui.test.junit4)
    testImplementation(libs.zstd.jni)
    testImplementation(libs.orgJson)
    testImplementation(libs.mockwebserver)
}
