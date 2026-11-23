# Stable and beta

- **Stable** (branch `main`): the release marked **Latest**. The app's update check only offers these. Known issues are at the
  top of [CHANGES.md](CHANGES.md).
- **Beta** (branch [`beta`](https://github.com/mummigast/ds-forever-linux/tree/beta)): bigger changes are tried here first and
  published as **pre-releases** (`linux-v<version>-beta.<n>`), each with its own APK, helper and notes. What a beta adds is in
  [CHANGES.md on the beta branch](https://github.com/mummigast/ds-forever-linux/blob/beta/CHANGES.md) and in each pre-release's notes
  on the [releases page](https://github.com/mummigast/ds-forever-linux/releases). When a beta has proven itself, it becomes the next
  stable release.

## Installing a beta

1. From the pre-release, download both the APK and `dsf-linux-helper-<version>.tar.gz` (the add-ons must match the app).
2. Install the APK over the stable one. It is signed with the same key, so your settings stay.
3. Unpack the helper and run its `./install.sh`.

To go back, install the latest stable release's APK and helper the same way. The app's update check never offers a beta.
