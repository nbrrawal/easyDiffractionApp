import QtQuick 2.13
import QtQuick.Controls 2.13
import QtQuick.XmlListModel 2.13

import easyAppGui.Globals 1.0 as EaGlobals
import easyAppGui.Style 1.0 as EaStyle
import easyAppGui.Elements 1.0 as EaElements
import easyAppGui.Components 1.0 as EaComponents
import easyAppGui.Logic 1.0 as EaLogic

import Gui.Globals 1.0 as ExGlobals

EaComponents.TableView {

    // Table model

    model: XmlListModel {
        xml: ExGlobals.Constants.proxy.backgroundAsXml
        query: "/root/item"

        XmlRole { name: "x"; query: "x/value/number()" }
        XmlRole { name: "y"; query: "y/value/number()" }

        XmlRole { name: "xId"; query: "x/key[4]/string()" }
        XmlRole { name: "yId"; query: "y/key[4]/string()" }

        onXmlChanged: print(EaLogic.Utils.prettyXml(xml))
    }

    // Table rows

    delegate: EaComponents.TableViewDelegate {

        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 2.5
            headerText: "No."
            text: model.index + 1
        }

        EaComponents.TableViewTextInput {
            id: xLabel
            horizontalAlignment: Text.AlignRight
            width: EaStyle.Sizes.fontPixelSize * 11.6
            headerText: "2theta"
            text: model.x
            onEditingFinished: editParameterValue(model.xId, text)
        }

        EaComponents.TableViewTextInput {
            id: yLabel
            horizontalAlignment: Text.AlignRight
            width: xLabel.width
            headerText: "Intensity"
            text: model.y
            onEditingFinished: editParameterValue(model.yId, text)
        }

        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 7
        }

        EaComponents.TableViewButton {
            headerText: "Del."
            fontIcon: "minus-circle"
            ToolTip.text: qsTr("Remove this point")
            onClicked: ExGlobals.Constants.proxy.removeBackgroundPoint(currentIndex)
        }

    }

    // Logic

    function editParameterValue(id, value) {
        ExGlobals.Constants.proxy.editParameterValue(id, parseFloat(value))
    }

}
