# Third-Party Notices

This file records important third-party software used or planned by **Hybrid Document to Markdown**. It supports attribution and release preparation; it is not legal advice and is not a replacement for the complete license texts shipped by each dependency.

## License boundaries

- The repository [MIT License](LICENSE) applies only to original project code and documentation that the project contributors are authorized to license.
- Microsoft MarkItDown and every other dependency retain their own copyright and license terms.
- Declaring a package in `requirements.in` or `requirements.txt` does not relicense that package under this project's MIT License.
- A future Windows executable may bundle Python packages and native libraries. The final distribution must include every notice and license required by the components actually shipped.

## Current primary components

| Component | Version | Role | Upstream license | Current status |
|---|---:|---|---|---|
| [Microsoft MarkItDown](https://github.com/microsoft/markitdown) | 0.1.9 | Primary document conversion engine | MIT | Installed and integrated |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) | 6.12.0 | Windows desktop framework | LGPL-3.0 / GPL-3.0 / commercial options | Installed and integrated |
| [Press Start 2P](https://github.com/google/fonts/tree/main/ofl/pressstart2p) | 3.000 | Pixel heading font | SIL Open Font License 1.1 | Bundled with OFL and FONTLOG |
| [pytest](https://github.com/pytest-dev/pytest) | 9.2.0 | Development testing | MIT | Development only |

## Format-specific runtime dependencies

These packages are installed through the selected MarkItDown extras. Versions reflect the current development lock file.

| Component | Version | Used for | License | Notice requirement |
|---|---:|---|---|---|
| [Mammoth](https://github.com/mwilliamson/python-mammoth) | 1.13.0 | DOCX conversion | BSD-2-Clause | Retain copyright, conditions, and disclaimer |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | 0.11.10 | PDF extraction | MIT | Retain copyright and license notice |
| [python-pptx](https://github.com/scanny/python-pptx) | 1.0.2 | PPTX conversion | MIT | Retain copyright and license notice |
| [openpyxl](https://openpyxl.readthedocs.io/) | 3.1.5 | XLSX processing | MIT | Retain copyright and license notice |
| [pandas](https://pandas.pydata.org/) | 3.1.1 | XLSX/tabular processing | BSD-3-Clause | Retain copyright, conditions, and disclaimer |
| [XlsxWriter](https://github.com/jmcnamara/XlsxWriter) | 3.3.1 | Workbook support installed through `python-pptx` | BSD-2-Clause | Retain copyright, conditions, and disclaimer |

> [!NOTE]
> This table highlights the primary and format-specific packages. MarkItDown, PySide6, and those packages have additional transitive dependencies. A complete machine-generated dependency and license inventory must be produced from the final release environment during Phase F.

## Microsoft MarkItDown attribution

MarkItDown is licensed separately from this project under the MIT License. Its upstream license identifies Microsoft Corporation as the copyright holder.

<details>
<summary>Microsoft MarkItDown MIT License</summary>

```text
MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

</details>

Source: [Microsoft MarkItDown LICENSE](https://github.com/microsoft/markitdown/blob/main/LICENSE)

## PySide6 and Qt distribution note

The development environment currently uses the community PySide6 wheels. Qt for Python documents open-source LGPLv3/GPLv3 and commercial licensing paths.

Before distributing a Windows build:

- Identify the Qt and PySide6 modules actually bundled.
- Select and document the applicable Qt licensing path.
- Include the required Qt, PySide6, and third-party license texts.
- Preserve the rights required by the selected LGPL/GPL terms.
- Audit Qt WebEngine and Chromium notices if WebEngine is shipped.
- Do not assume that the repository's MIT License replaces Qt's terms.

Official references:

- [Qt for Python licensing overview](https://doc.qt.io/qtforpython-6/)
- [Qt licensing](https://doc.qt.io/qt-6/licensing.html)
- [Qt for Python third-party licenses](https://doc.qt.io/qtforpython-6/licenses.html)

## Release compliance checklist

Before publishing an executable or installer:

1. Rebuild from a clean, pinned release environment.
2. Record the full direct and transitive dependency tree.
3. Generate a complete license inventory or software bill of materials.
4. Confirm which Python packages, Qt modules, native binaries, and plugins are bundled.
5. Include the MarkItDown MIT notice and all required third-party notices.
6. Reproduce the applicable MIT and BSD copyright notices and license conditions.
7. Complete the Qt/PySide6 compliance review for the chosen packaging method.
8. Audit Qt WebEngine/Chromium separately if included.
9. Recheck this document against the exact release artifact.

## Independence statement

This is an independent portfolio project. It is not affiliated with, sponsored by, or endorsed by Microsoft, The Qt Company, or other upstream maintainers.
