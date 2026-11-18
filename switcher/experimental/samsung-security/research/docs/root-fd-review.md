# Opened-descriptor export review

The combined image and installer FD patches pass this bounded source review. Nine individual patch joins and inverses reproduce their afterimages and held originals. Composition across seven unique source targets is exact, including both base and derived RootScript variants. No source was changed or executed by the reviewer.

The image launchers now export their held FD3 at all three external `stat` calls, the external SHA-256 command and the final native exec. The same opened image still supplies metadata, hashing and execution; filenames, build pins, arguments and native same-image verification remain unchanged.

The bootstrap explicitly exports its fixed directory/file anchors at the actual external `stat`, hash, `head`, `mkdir`, `rm` and `rmdir` invocations. Its child shell borrows FD4 to open the private script, while closing only its child copies of FD3, FD5 and FD6. The initial image patch omitted the already-derived overlay child; its successor includes that exact fourth target. Applying the image changes first and installer utility changes second reproduces both combined variants and reverses exactly.

The installer exports fixed FD8/9/7 for stage/bin/target metadata, FD5 for private payload paths and FD6 for payload metadata, hashing, ownership, permissions and input. Hard-link publication exports both private-directory FD5 and target-directory FD9. Hash helpers export at `sha256sum` itself, avoiding reliance on a function-level redirection propagating into a pipeline child. No caller-selected descriptor, pass-all-FDs strategy, changed ownership policy or overwrite fallback is introduced.

The existing occupied-slot refusal, exclusive private work directory, bounded prefix/native feed and EOF, exact length/hash/inode checks, regular/nonlink profile, atomic no-clobber publication and consumed-once cleanup remain. Root's saved read-only Android stat/hash/directory probes show failure with implicit descriptors and success with explicit exports. They support this inheritance correction; they do not prove an installer write, native execution, installed image or runtime custody.

Existing Java mirrors, generated overlays, source receipts and compiled packages do not automatically cover corrected bytes. Their final copying or regeneration and fresh Kotlin/SDK/packaging checks remain root-owned work. The image patch contains mixed LF/CRLF source-context lines; the independent data reader preserves each original source's exact line-ending style and verifies the resulting bytes. Its initial LF-only reader refusal was retained before that reader-only correction.

No shell, native helper, installer, compiler, model, phone or Git workflow ran in this review. No default launch, permission, security, guest admission or device acceptance follows. Exact patch/source joins and limitations are in `inventory/root-fd-review.json` and the immutable private proof.
