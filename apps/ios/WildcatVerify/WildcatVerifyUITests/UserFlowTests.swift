import XCTest

/// Walks through the app the way a person would. No network is needed: the
/// flows use the bundled examples, the About sheet, and input validation.
@MainActor
final class UserFlowTests: XCTestCase {
    private var app = XCUIApplication()

    private func launch(contentSize: String? = nil, dark: Bool = false, showSiriTip: Bool = false, showWelcome: Bool = false) {
        continueAfterFailure = false
        app = XCUIApplication()
        // The first-run guide is tested on its own; every other test starts past it.
        app.launchArguments += ["-settings.welcomeSeen", showWelcome ? "NO" : "YES"]
        if showSiriTip {
            // Argument-domain defaults win over anything saved by earlier runs.
            app.launchArguments += ["-settings.siriTipDismissed", "NO"]
        }
        if let contentSize {
            app.launchArguments += ["-UIPreferredContentSizeCategoryName", contentSize]
        }
        if dark {
            app.launchArguments += ["-AppleInterfaceStyle", "Dark"]
        }
        app.launch()
    }

    /// Waits until an element can be tapped (the Check card fades in on launch).
    @discardableResult
    private func waitUntilHittable(_ element: XCUIElement, timeout: TimeInterval = 5) -> Bool {
        let hittable = expectation(for: NSPredicate(format: "exists == true AND isHittable == true"), evaluatedWith: element)
        return XCTWaiter().wait(for: [hittable], timeout: timeout) == .completed
    }

    private func tab(_ name: String) -> XCUIElement {
        app.tabBars.buttons[name]
    }

    /// Taps a tab once the tab bar is ready, retrying once if a tap during
    /// launch was dropped.
    private func selectTab(_ name: String) {
        let button = tab(name)
        XCTAssertTrue(waitUntilHittable(button), "Tab \(name) never became tappable")
        button.tap()
        if !button.isSelected { button.tap() }
        XCTAssertTrue(button.isSelected, "Couldn't switch to \(name)")
    }

    // MARK: Launch and tabs

    func testOpensOnCheckWithAllTabs() {
        launch()
        XCTAssertTrue(app.staticTexts["WildcatVerify"].waitForExistence(timeout: 5))
        for name in ["Feed", "Learn", "Check", "My Checks", "Settings"] {
            XCTAssertTrue(tab(name).exists, "Missing tab \(name)")
        }
        XCTAssertTrue(tab("Check").isSelected)
    }

    // MARK: Check input

    func testCheckPostEnablesOnlyWithALink() {
        launch()
        let field = app.textFields["linkField"]
        let checkPost = app.buttons["Check Post"]
        XCTAssertTrue(waitUntilHittable(field))
        XCTAssertFalse(checkPost.isEnabled, "Nothing to check yet")

        field.tap()
        field.typeText("   ")
        XCTAssertFalse(checkPost.isEnabled, "Spaces aren't a link")

        field.typeText("bsky.app/profile/a/post/b")
        XCTAssertTrue(checkPost.isEnabled)

        app.buttons["Clear Link"].tap()
        XCTAssertFalse(checkPost.isEnabled, "Clearing the field disables the button again")
    }

    func testInvalidLinkShowsARecoverableError() {
        launch()
        let field = app.textFields["linkField"]
        XCTAssertTrue(waitUntilHittable(field))
        field.tap()
        field.typeText("https://example.com/not-bluesky")
        app.buttons["Check Post"].tap()

        let alert = app.alerts["Couldn't Check Image"]
        XCTAssertTrue(alert.waitForExistence(timeout: 5))
        XCTAssertTrue(alert.staticTexts.containing(NSPredicate(format: "label CONTAINS 'Bluesky post link'")).firstMatch.exists)
        alert.buttons.firstMatch.tap()

        XCTAssertFalse(alert.exists)
        XCTAssertEqual(field.value as? String, "https://example.com/not-bluesky", "The link stays so it can be fixed")
    }

    func testPhotoPickerOpens() {
        launch()
        let dropzone = app.buttons["Choose photo or screenshot to check"]
        XCTAssertTrue(waitUntilHittable(dropzone))
        dropzone.tap()
        // The system picker runs out of process; its Cancel/close control proves it appeared.
        let picker = app.otherElements["PhotosPicker"].exists
            || app.buttons["Cancel"].waitForExistence(timeout: 5)
            || app.buttons["Close"].waitForExistence(timeout: 2)
        XCTAssertTrue(picker, "Photo picker should appear")
    }

    func testPracticeRoundPlaysInPlace() {
        launch()
        selectTab("Learn")
        for question in 1...8 {
            let answer = app.buttons["answer-ai"]
            for _ in 0..<4 where !(answer.exists && answer.isHittable) { app.swipeUp() }
            XCTAssertTrue(waitUntilHittable(answer), "No answers on question \(question)")
            answer.tap()

            let next = app.buttons[question == 8 ? "See Results" : "Next Post"]
            for _ in 0..<4 where !(next.exists && next.isHittable) { app.swipeUp() }
            XCTAssertTrue(next.waitForExistence(timeout: 3), "Feedback and Next after question \(question)")
            let picked = app.descendants(matching: .any)["answer-ai"]
            XCTAssertTrue((picked.value as? String)?.hasPrefix("Your answer") == true, "Your pick is marked once revealed")
            XCTAssertFalse(app.buttons["answer-ai"].exists, "Revealed answers stop being buttons")
            XCTAssertTrue(app.navigationBars["Learn"].exists, "The round stays on the Learn screen")
            next.tap()
        }

        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label ENDSWITH ' right'")).firstMatch.waitForExistence(timeout: 5))
        let again = app.buttons["Play Again"]
        for _ in 0..<6 where !again.isHittable { app.swipeUp() }
        again.tap()
        XCTAssertTrue(app.buttons["answer-ai"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["answer-ai"].isEnabled)
    }

    func testClueGuideOpensOnTheChosenGroup() {
        launch()
        selectTab("Learn")
        let editing = app.buttons["clueGroup-Editing"]
        for _ in 0..<4 where !editing.isHittable { app.swipeUp() }
        XCTAssertTrue(waitUntilHittable(editing))
        editing.tap()
        XCTAssertTrue(app.navigationBars["Clue Guide"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Editing"].isSelected)
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label BEGINSWITH 'Shadows'")).firstMatch.exists)
        app.buttons["AI"].tap()
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label BEGINSWITH 'Lighting'")).firstMatch.waitForExistence(timeout: 3))
    }

    func testFeedShowsPostsOrAClearError() {
        launch()
        selectTab("Feed")
        XCTAssertTrue(app.navigationBars["Feed"].waitForExistence(timeout: 5))
        // Live network: either posts arrive or the retry screen shows. Never stuck.
        let loaded = app.staticTexts["TRENDING ON BLUESKY"].waitForExistence(timeout: 15)
            || app.staticTexts["Trending on Bluesky"].exists
            || app.staticTexts["Couldn't Load the Feed"].exists
        XCTAssertTrue(loaded, "Feed should show posts or an error")
    }

    func testSettingsDefaultsArePrivate() {
        launch()
        selectTab("Settings")
        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 5))
        let keep = app.switches["Keep My Checks"]
        XCTAssertTrue(keep.waitForExistence(timeout: 5))
        XCTAssertEqual(keep.value as? String, "0", "Saving history is off by default")
        XCTAssertTrue(app.switches["Show Heatmap"].exists)
        XCTAssertTrue(app.switches["Haptics"].exists)
        let erase = app.buttons["Erase All Data"]
        for _ in 0..<4 where !erase.isHittable { app.swipeUp() }
        XCTAssertTrue(erase.isHittable)
    }

    func testCreditsShowTheModelLicense() {
        launch()
        selectTab("Settings")
        let row = app.buttons["creditsRow"]
        for _ in 0..<4 where !row.isHittable { app.swipeUp() }
        XCTAssertTrue(waitUntilHittable(row))
        row.tap()
        XCTAssertTrue(app.navigationBars["Credits"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["CommunityForensics ViT"].exists)
        let license = app.staticTexts.containing(NSPredicate(format: "label CONTAINS 'Copyright (c) 2025 Jeongsoo Park'")).firstMatch
        for _ in 0..<6 where !license.exists { app.swipeUp() }
        XCTAssertTrue(license.exists, "The MIT notice must ship with the app")
    }

    func testTermsAndHiddenAccountsAreInSettings() {
        launch()
        selectTab("Settings")
        let hidden = app.buttons["hiddenAccountsRow"]
        XCTAssertTrue(waitUntilHittable(hidden))
        hidden.tap()
        XCTAssertTrue(app.navigationBars["Hidden Accounts"].waitForExistence(timeout: 5))
        app.navigationBars.buttons.firstMatch.tap()

        let terms = app.buttons["termsRow"]
        for _ in 0..<4 where !terms.isHittable { app.swipeUp() }
        XCTAssertTrue(waitUntilHittable(terms))
        terms.tap()
        XCTAssertTrue(app.navigationBars["Terms of Use"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Verdicts are estimates"].exists || app.staticTexts["VERDICTS ARE ESTIMATES"].exists)
    }

    // MARK: First run

    func testFirstLaunchShowsWaysToCheckOnce() {
        launch(showWelcome: true)
        let done = app.buttons["welcomeDone"]
        XCTAssertTrue(done.waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Hold the photo, tap Share"].exists)
        done.tap()
        XCTAssertTrue(app.textFields["linkField"].waitForExistence(timeout: 5))
        XCTAssertFalse(done.exists)
    }

    // MARK: Siri

    func testSettingsOpensSiriSetup() {
        launch()
        selectTab("Settings")
        let row = app.buttons["siriSetupRow"]
        XCTAssertTrue(waitUntilHittable(row))
        row.tap()
        XCTAssertTrue(app.navigationBars["Siri & Shortcuts"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Check posts without leaving Bluesky"].exists)
        XCTAssertFalse(app.buttons["addShortcut"].exists, "No iCloud link yet, so only the manual steps")
    }

    func testSiriTipOpensSetup() {
        launch(showSiriTip: true)
        let tip = app.buttons["siriTip"]
        // The copied-link card can push the tip below the fold.
        XCTAssertTrue(tip.waitForExistence(timeout: 5))
        for _ in 0..<3 where !tip.isHittable { app.swipeUp() }
        XCTAssertTrue(waitUntilHittable(tip))
        tip.tap()
        XCTAssertTrue(tab("Settings").isSelected)
        XCTAssertTrue(app.navigationBars["Siri & Shortcuts"].waitForExistence(timeout: 5))
    }

    func testSiriTipCanBeDismissed() {
        launch(showSiriTip: true)
        let tip = app.buttons["siriTip"]
        // The copied-link card can push the tip below the fold.
        XCTAssertTrue(tip.waitForExistence(timeout: 5))
        for _ in 0..<3 where !tip.isHittable { app.swipeUp() }
        XCTAssertTrue(waitUntilHittable(tip))
        app.buttons["dismissSiriTip"].tap()
        let gone = expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: tip)
        wait(for: [gone], timeout: 5)
    }

    // MARK: My Checks

    func testEmptyMyChecksLeadsToCheck() {
        launch()
        selectTab("My Checks")
        XCTAssertTrue(app.staticTexts["No Checks Yet"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Clear"].isEnabled, "Nothing to clear")
        app.buttons["Check an Image"].tap()
        XCTAssertTrue(tab("Check").isSelected)
    }

    // MARK: About and privacy

    func testAboutSheetShowsPrivacyPolicy() {
        launch()
        let about = app.buttons["About WildcatVerify"]
        XCTAssertTrue(about.waitForExistence(timeout: 5))
        about.tap()

        XCTAssertTrue(app.navigationBars["About"].waitForExistence(timeout: 5))
        let policy = app.buttons["Privacy Policy"]
        for _ in 0..<6 where !(policy.exists && policy.isHittable) { app.swipeUp() }
        policy.tap()
        XCTAssertTrue(app.navigationBars["Privacy Policy"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Photos you choose"].exists || app.staticTexts["PHOTOS YOU CHOOSE"].exists)

        app.navigationBars.buttons.firstMatch.tap()
        app.buttons["Done"].tap()
        XCTAssertFalse(app.navigationBars["About"].waitForExistence(timeout: 2))
    }

    func testAboutIsReachableFromEveryTab() {
        launch()
        for name in ["Learn", "My Checks", "Check"] {
            tab(name).tap()
            let about = app.buttons["About WildcatVerify"]
            XCTAssertTrue(about.waitForExistence(timeout: 5), "No About on \(name)")
        }
    }

    // MARK: Accessibility settings

    func testLargestTextKeepsControlsReachable() {
        launch(contentSize: "UICTContentSizeCategoryAccessibilityXXXL")
        let field = app.textFields["linkField"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        // Sections fade in on first appear, and big text may push the field down.
        let hittable = expectation(for: NSPredicate(format: "isHittable == true"), evaluatedWith: field)
        if !field.isHittable { app.swipeUp() }
        wait(for: [hittable], timeout: 5)
        XCTAssertTrue(app.buttons["Check Post"].exists)
        XCTAssertTrue(tab("Learn").isHittable)

        selectTab("Learn")
        // Answers stack at big sizes; scroll to them like a person would.
        let answer = app.buttons["answer-edited"]
        for _ in 0..<8 where !answer.exists || !answer.isHittable { app.swipeUp() }
        XCTAssertTrue(answer.isHittable)
        answer.tap()
        XCTAssertTrue(app.buttons["Next Post"].waitForExistence(timeout: 5), "Reveal happens in place")
    }

    func testDarkModeLaunches() {
        launch(dark: true)
        XCTAssertTrue(app.textFields["linkField"].waitForExistence(timeout: 5))
        selectTab("Learn")
        XCTAssertTrue(app.navigationBars["Learn"].waitForExistence(timeout: 5))
    }
}
