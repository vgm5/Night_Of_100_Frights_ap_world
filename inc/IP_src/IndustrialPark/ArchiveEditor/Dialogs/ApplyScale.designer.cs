﻿namespace IndustrialPark
{
    partial class ApplyScale
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.button1 = new System.Windows.Forms.Button();
            this.button2 = new System.Windows.Forms.Button();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.numericUpDownZ = new System.Windows.Forms.NumericUpDown();
            this.numericUpDownY = new System.Windows.Forms.NumericUpDown();
            this.numericUpDownX = new System.Windows.Forms.NumericUpDown();
            this.checkedListBoxAssetTypes = new System.Windows.Forms.CheckedListBox();
            this.label1 = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.checkBoxBakeScales = new System.Windows.Forms.CheckBox();
            this.checkBoxBakeNpcScales = new System.Windows.Forms.CheckBox();
            this.groupBox1.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.numericUpDownZ)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numericUpDownY)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.numericUpDownX)).BeginInit();
            this.SuspendLayout();
            // 
            // button1
            // 
            this.button1.Location = new System.Drawing.Point(168, 303);
            this.button1.Name = "button1";
            this.button1.Size = new System.Drawing.Size(75, 23);
            this.button1.TabIndex = 1;
            this.button1.Text = "Apply";
            this.button1.UseVisualStyleBackColor = true;
            this.button1.Click += new System.EventHandler(this.button1_Click);
            // 
            // button2
            // 
            this.button2.DialogResult = System.Windows.Forms.DialogResult.Cancel;
            this.button2.Location = new System.Drawing.Point(249, 303);
            this.button2.Name = "button2";
            this.button2.Size = new System.Drawing.Size(75, 23);
            this.button2.TabIndex = 2;
            this.button2.Text = "Cancel";
            this.button2.UseVisualStyleBackColor = true;
            this.button2.Click += new System.EventHandler(this.button2_Click);
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.numericUpDownZ);
            this.groupBox1.Controls.Add(this.numericUpDownY);
            this.groupBox1.Controls.Add(this.numericUpDownX);
            this.groupBox1.Location = new System.Drawing.Point(12, 12);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Size = new System.Drawing.Size(319, 49);
            this.groupBox1.TabIndex = 3;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Scale (X, Y, Z)";
            // 
            // numericUpDownZ
            // 
            this.numericUpDownZ.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.numericUpDownZ.DecimalPlaces = 4;
            this.numericUpDownZ.Location = new System.Drawing.Point(214, 19);
            this.numericUpDownZ.Name = "numericUpDownZ";
            this.numericUpDownZ.Size = new System.Drawing.Size(98, 20);
            this.numericUpDownZ.TabIndex = 6;
            this.numericUpDownZ.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numericUpDownZ.ValueChanged += new System.EventHandler(this.numericUpDown_ValueChanged);
            // 
            // numericUpDownY
            // 
            this.numericUpDownY.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.numericUpDownY.DecimalPlaces = 4;
            this.numericUpDownY.Location = new System.Drawing.Point(110, 19);
            this.numericUpDownY.Name = "numericUpDownY";
            this.numericUpDownY.Size = new System.Drawing.Size(98, 20);
            this.numericUpDownY.TabIndex = 5;
            this.numericUpDownY.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numericUpDownY.ValueChanged += new System.EventHandler(this.numericUpDown_ValueChanged);
            // 
            // numericUpDownX
            // 
            this.numericUpDownX.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.numericUpDownX.DecimalPlaces = 4;
            this.numericUpDownX.Location = new System.Drawing.Point(6, 19);
            this.numericUpDownX.Name = "numericUpDownX";
            this.numericUpDownX.Size = new System.Drawing.Size(98, 20);
            this.numericUpDownX.TabIndex = 4;
            this.numericUpDownX.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numericUpDownX.ValueChanged += new System.EventHandler(this.numericUpDown_ValueChanged);
            // 
            // checkedListBoxAssetTypes
            // 
            this.checkedListBoxAssetTypes.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.checkedListBoxAssetTypes.FormattingEnabled = true;
            this.checkedListBoxAssetTypes.Location = new System.Drawing.Point(12, 95);
            this.checkedListBoxAssetTypes.Name = "checkedListBoxAssetTypes";
            this.checkedListBoxAssetTypes.Size = new System.Drawing.Size(312, 167);
            this.checkedListBoxAssetTypes.TabIndex = 4;
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(15, 64);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(35, 13);
            this.label1.TabIndex = 5;
            this.label1.Text = "label1";
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(15, 79);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(104, 13);
            this.label2.TabIndex = 6;
            this.label2.Text = "Asset types to scale:";
            // 
            // checkBoxBakeScales
            // 
            this.checkBoxBakeScales.AutoSize = true;
            this.checkBoxBakeScales.Checked = true;
            this.checkBoxBakeScales.CheckState = System.Windows.Forms.CheckState.Checked;
            this.checkBoxBakeScales.Location = new System.Drawing.Point(18, 267);
            this.checkBoxBakeScales.Name = "checkBoxBakeScales";
            this.checkBoxBakeScales.Size = new System.Drawing.Size(132, 30);
            this.checkBoxBakeScales.TabIndex = 7;
            this.checkBoxBakeScales.Text = "Bake unproportional\r\nscales on entity assets";
            this.checkBoxBakeScales.UseVisualStyleBackColor = true;
            // 
            // checkBoxBakeNpcScales
            // 
            this.checkBoxBakeNpcScales.AutoSize = true;
            this.checkBoxBakeNpcScales.Location = new System.Drawing.Point(18, 300);
            this.checkBoxBakeNpcScales.Name = "checkBoxBakeNpcScales";
            this.checkBoxBakeNpcScales.Size = new System.Drawing.Size(128, 30);
            this.checkBoxBakeNpcScales.TabIndex = 8;
            this.checkBoxBakeNpcScales.Text = "Apply and bake scale\r\nto NPCs";
            this.checkBoxBakeNpcScales.UseVisualStyleBackColor = true;
            // 
            // ApplyScale
            // 
            this.AcceptButton = this.button1;
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.CancelButton = this.button2;
            this.ClientSize = new System.Drawing.Size(336, 337);
            this.Controls.Add(this.checkBoxBakeNpcScales);
            this.Controls.Add(this.checkBoxBakeScales);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.checkedListBoxAssetTypes);
            this.Controls.Add(this.groupBox1);
            this.Controls.Add(this.button2);
            this.Controls.Add(this.button1);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.Name = "ApplyScale";
            this.ShowIcon = false;
            this.ShowInTaskbar = false;
            this.Text = "Apply Scale";
            this.groupBox1.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.numericUpDownZ)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numericUpDownY)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.numericUpDownX)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion
        private System.Windows.Forms.Button button1;
        private System.Windows.Forms.Button button2;
        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.NumericUpDown numericUpDownZ;
        private System.Windows.Forms.NumericUpDown numericUpDownY;
        private System.Windows.Forms.NumericUpDown numericUpDownX;
        private System.Windows.Forms.CheckedListBox checkedListBoxAssetTypes;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.CheckBox checkBoxBakeScales;
        private System.Windows.Forms.CheckBox checkBoxBakeNpcScales;
    }
}