using System.Windows.Forms;

namespace Adminpanel
{
    partial class RequestDetailsForm
    {
        private System.ComponentModel.IContainer components = null;

        private Label labelRequestNumber;
        private TextBox textBoxRequestNumber;
        private Label labelStatus;
        private TextBox textBoxStatus;
        private Label labelCreatedAt;
        private TextBox textBoxCreatedAt;
        private Label labelUser;
        private TextBox textBoxUser;
        private Label labelDescription;
        private TextBox textBoxDescription;
        private Label labelCoordinates;
        private TextBox textBoxCoordinates;
        private LinkLabel linkLabelMap;
        private LinkLabel linkLabelBot;
        private Label labelPhoto;
        private PictureBox pictureBoxPhoto;
        private Label labelVideo;
        private Button buttonClose;
        private Button buttonCopyNumber;
        private Panel panelMedia;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(RequestDetailsForm));
            this.labelRequestNumber = new System.Windows.Forms.Label();
            this.textBoxRequestNumber = new System.Windows.Forms.TextBox();
            this.labelStatus = new System.Windows.Forms.Label();
            this.textBoxStatus = new System.Windows.Forms.TextBox();
            this.labelCreatedAt = new System.Windows.Forms.Label();
            this.textBoxCreatedAt = new System.Windows.Forms.TextBox();
            this.labelUser = new System.Windows.Forms.Label();
            this.textBoxUser = new System.Windows.Forms.TextBox();
            this.labelDescription = new System.Windows.Forms.Label();
            this.textBoxDescription = new System.Windows.Forms.TextBox();
            this.labelCoordinates = new System.Windows.Forms.Label();
            this.textBoxCoordinates = new System.Windows.Forms.TextBox();
            this.linkLabelMap = new System.Windows.Forms.LinkLabel();
            this.linkLabelBot = new System.Windows.Forms.LinkLabel();
            this.labelPhoto = new System.Windows.Forms.Label();
            this.pictureBoxPhoto = new System.Windows.Forms.PictureBox();
            this.labelVideo = new System.Windows.Forms.Label();
            this.buttonClose = new System.Windows.Forms.Button();
            this.buttonCopyNumber = new System.Windows.Forms.Button();
            this.panelMedia = new System.Windows.Forms.Panel();
            ((System.ComponentModel.ISupportInitialize)(this.pictureBoxPhoto)).BeginInit();
            this.panelMedia.SuspendLayout();
            this.SuspendLayout();
            // 
            // labelRequestNumber
            // 
            this.labelRequestNumber.AutoSize = true;
            this.labelRequestNumber.BackColor = System.Drawing.Color.Transparent;
            this.labelRequestNumber.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelRequestNumber.Location = new System.Drawing.Point(12, 15);
            this.labelRequestNumber.Name = "labelRequestNumber";
            this.labelRequestNumber.Size = new System.Drawing.Size(125, 21);
            this.labelRequestNumber.TabIndex = 0;
            this.labelRequestNumber.Text = "Номер заявки:";
            // 
            // textBoxRequestNumber
            // 
            this.textBoxRequestNumber.BackColor = System.Drawing.SystemColors.Window;
            this.textBoxRequestNumber.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.textBoxRequestNumber.Location = new System.Drawing.Point(174, 12);
            this.textBoxRequestNumber.Name = "textBoxRequestNumber";
            this.textBoxRequestNumber.ReadOnly = true;
            this.textBoxRequestNumber.Size = new System.Drawing.Size(209, 29);
            this.textBoxRequestNumber.TabIndex = 1;
            // 
            // labelStatus
            // 
            this.labelStatus.AutoSize = true;
            this.labelStatus.BackColor = System.Drawing.Color.Transparent;
            this.labelStatus.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelStatus.Location = new System.Drawing.Point(10, 80);
            this.labelStatus.Name = "labelStatus";
            this.labelStatus.Size = new System.Drawing.Size(69, 21);
            this.labelStatus.TabIndex = 2;
            this.labelStatus.Text = "Статус:";
            // 
            // textBoxStatus
            // 
            this.textBoxStatus.BackColor = System.Drawing.SystemColors.Window;
            this.textBoxStatus.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.textBoxStatus.Location = new System.Drawing.Point(174, 77);
            this.textBoxStatus.Name = "textBoxStatus";
            this.textBoxStatus.ReadOnly = true;
            this.textBoxStatus.Size = new System.Drawing.Size(209, 29);
            this.textBoxStatus.TabIndex = 3;
            // 
            // labelCreatedAt
            // 
            this.labelCreatedAt.AutoSize = true;
            this.labelCreatedAt.BackColor = System.Drawing.Color.Transparent;
            this.labelCreatedAt.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelCreatedAt.Location = new System.Drawing.Point(12, 45);
            this.labelCreatedAt.Name = "labelCreatedAt";
            this.labelCreatedAt.Size = new System.Drawing.Size(130, 21);
            this.labelCreatedAt.TabIndex = 4;
            this.labelCreatedAt.Text = "Дата создания:";
            // 
            // textBoxCreatedAt
            // 
            this.textBoxCreatedAt.BackColor = System.Drawing.SystemColors.Window;
            this.textBoxCreatedAt.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.textBoxCreatedAt.Location = new System.Drawing.Point(174, 42);
            this.textBoxCreatedAt.Name = "textBoxCreatedAt";
            this.textBoxCreatedAt.ReadOnly = true;
            this.textBoxCreatedAt.Size = new System.Drawing.Size(209, 29);
            this.textBoxCreatedAt.TabIndex = 5;
            // 
            // labelUser
            // 
            this.labelUser.AutoSize = true;
            this.labelUser.BackColor = System.Drawing.Color.Transparent;
            this.labelUser.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelUser.Location = new System.Drawing.Point(10, 110);
            this.labelUser.Name = "labelUser";
            this.labelUser.Size = new System.Drawing.Size(124, 21);
            this.labelUser.TabIndex = 6;
            this.labelUser.Text = "Пользователь:";
            // 
            // textBoxUser
            // 
            this.textBoxUser.BackColor = System.Drawing.SystemColors.Window;
            this.textBoxUser.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.textBoxUser.Location = new System.Drawing.Point(174, 107);
            this.textBoxUser.Name = "textBoxUser";
            this.textBoxUser.ReadOnly = true;
            this.textBoxUser.Size = new System.Drawing.Size(209, 29);
            this.textBoxUser.TabIndex = 7;
            // 
            // labelDescription
            // 
            this.labelDescription.AutoSize = true;
            this.labelDescription.BackColor = System.Drawing.Color.Transparent;
            this.labelDescription.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelDescription.Location = new System.Drawing.Point(14, 165);
            this.labelDescription.Name = "labelDescription";
            this.labelDescription.Size = new System.Drawing.Size(93, 21);
            this.labelDescription.TabIndex = 8;
            this.labelDescription.Text = "Описание:";
            // 
            // textBoxDescription
            // 
            this.textBoxDescription.BackColor = System.Drawing.SystemColors.Window;
            this.textBoxDescription.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.textBoxDescription.Location = new System.Drawing.Point(131, 162);
            this.textBoxDescription.Multiline = true;
            this.textBoxDescription.Name = "textBoxDescription";
            this.textBoxDescription.ReadOnly = true;
            this.textBoxDescription.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.textBoxDescription.Size = new System.Drawing.Size(477, 100);
            this.textBoxDescription.TabIndex = 9;
            // 
            // labelCoordinates
            // 
            this.labelCoordinates.AutoSize = true;
            this.labelCoordinates.BackColor = System.Drawing.Color.Transparent;
            this.labelCoordinates.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelCoordinates.Location = new System.Drawing.Point(14, 275);
            this.labelCoordinates.Name = "labelCoordinates";
            this.labelCoordinates.Size = new System.Drawing.Size(115, 21);
            this.labelCoordinates.TabIndex = 10;
            this.labelCoordinates.Text = "Координаты:";
            // 
            // textBoxCoordinates
            // 
            this.textBoxCoordinates.BackColor = System.Drawing.SystemColors.Window;
            this.textBoxCoordinates.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.textBoxCoordinates.Location = new System.Drawing.Point(131, 272);
            this.textBoxCoordinates.Name = "textBoxCoordinates";
            this.textBoxCoordinates.ReadOnly = true;
            this.textBoxCoordinates.Size = new System.Drawing.Size(193, 29);
            this.textBoxCoordinates.TabIndex = 11;
            // 
            // linkLabelMap
            // 
            this.linkLabelMap.AutoSize = true;
            this.linkLabelMap.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.linkLabelMap.Location = new System.Drawing.Point(330, 275);
            this.linkLabelMap.Name = "linkLabelMap";
            this.linkLabelMap.Size = new System.Drawing.Size(154, 21);
            this.linkLabelMap.TabIndex = 12;
            this.linkLabelMap.TabStop = true;
            this.linkLabelMap.Text = "Показать на карте";
            this.linkLabelMap.LinkClicked += new System.Windows.Forms.LinkLabelLinkClickedEventHandler(this.linkLabelMap_LinkClicked);
            // 
            // linkLabelBot
            // 
            this.linkLabelBot.AutoSize = true;
            this.linkLabelBot.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.linkLabelBot.Location = new System.Drawing.Point(14, 320);
            this.linkLabelBot.Name = "linkLabelBot";
            this.linkLabelBot.Size = new System.Drawing.Size(136, 21);
            this.linkLabelBot.TabIndex = 13;
            this.linkLabelBot.TabStop = true;
            this.linkLabelBot.Text = "Открыть в боте";
            this.linkLabelBot.LinkClicked += new System.Windows.Forms.LinkLabelLinkClickedEventHandler(this.linkLabelBot_LinkClicked);
            // 
            // labelPhoto
            // 
            this.labelPhoto.AutoSize = true;
            this.labelPhoto.BackColor = System.Drawing.Color.Transparent;
            this.labelPhoto.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelPhoto.Location = new System.Drawing.Point(10, 10);
            this.labelPhoto.Name = "labelPhoto";
            this.labelPhoto.Size = new System.Drawing.Size(56, 21);
            this.labelPhoto.TabIndex = 14;
            this.labelPhoto.Text = "Фото:";
            // 
            // pictureBoxPhoto
            // 
            this.pictureBoxPhoto.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.pictureBoxPhoto.Location = new System.Drawing.Point(72, 10);
            this.pictureBoxPhoto.Name = "pictureBoxPhoto";
            this.pictureBoxPhoto.Size = new System.Drawing.Size(300, 200);
            this.pictureBoxPhoto.TabIndex = 15;
            this.pictureBoxPhoto.TabStop = false;
            // 
            // labelVideo
            // 
            this.labelVideo.AutoSize = true;
            this.labelVideo.BackColor = System.Drawing.Color.Transparent;
            this.labelVideo.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.labelVideo.Location = new System.Drawing.Point(10, 220);
            this.labelVideo.Name = "labelVideo";
            this.labelVideo.Size = new System.Drawing.Size(64, 21);
            this.labelVideo.TabIndex = 16;
            this.labelVideo.Text = "Видео:";
            // 
            // buttonClose
            // 
            this.buttonClose.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right)));
            this.buttonClose.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.buttonClose.Location = new System.Drawing.Point(492, 387);
            this.buttonClose.Name = "buttonClose";
            this.buttonClose.Size = new System.Drawing.Size(103, 43);
            this.buttonClose.TabIndex = 17;
            this.buttonClose.Text = "Закрыть";
            this.buttonClose.UseVisualStyleBackColor = true;
            this.buttonClose.Click += new System.EventHandler(this.buttonClose_Click);
            // 
            // buttonCopyNumber
            // 
            this.buttonCopyNumber.Font = new System.Drawing.Font("Times New Roman", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.buttonCopyNumber.Location = new System.Drawing.Point(393, 12);
            this.buttonCopyNumber.Name = "buttonCopyNumber";
            this.buttonCopyNumber.Size = new System.Drawing.Size(133, 29);
            this.buttonCopyNumber.TabIndex = 18;
            this.buttonCopyNumber.Text = "Копировать";
            this.buttonCopyNumber.UseVisualStyleBackColor = true;
            this.buttonCopyNumber.Click += new System.EventHandler(this.buttonCopyNumber_Click);
            // 
            // panelMedia
            // 
            this.panelMedia.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.panelMedia.BorderStyle = System.Windows.Forms.BorderStyle.FixedSingle;
            this.panelMedia.Controls.Add(this.labelPhoto);
            this.panelMedia.Controls.Add(this.pictureBoxPhoto);
            this.panelMedia.Controls.Add(this.labelVideo);
            this.panelMedia.Location = new System.Drawing.Point(620, 17);
            this.panelMedia.Name = "panelMedia";
            this.panelMedia.Size = new System.Drawing.Size(380, 413);
            this.panelMedia.TabIndex = 19;
            // 
            // RequestDetailsForm
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(1020, 450);
            this.Controls.Add(this.panelMedia);
            this.Controls.Add(this.buttonCopyNumber);
            this.Controls.Add(this.buttonClose);
            this.Controls.Add(this.linkLabelBot);
            this.Controls.Add(this.linkLabelMap);
            this.Controls.Add(this.textBoxCoordinates);
            this.Controls.Add(this.labelCoordinates);
            this.Controls.Add(this.textBoxDescription);
            this.Controls.Add(this.labelDescription);
            this.Controls.Add(this.textBoxUser);
            this.Controls.Add(this.labelUser);
            this.Controls.Add(this.textBoxCreatedAt);
            this.Controls.Add(this.labelCreatedAt);
            this.Controls.Add(this.textBoxStatus);
            this.Controls.Add(this.labelStatus);
            this.Controls.Add(this.textBoxRequestNumber);
            this.Controls.Add(this.labelRequestNumber);
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.Name = "RequestDetailsForm";
            this.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent;
            this.Text = "Детали заявки";
            this.Paint += new System.Windows.Forms.PaintEventHandler(this.RequestsDetailsForm_Paint);
            ((System.ComponentModel.ISupportInitialize)(this.pictureBoxPhoto)).EndInit();
            this.panelMedia.ResumeLayout(false);
            this.panelMedia.PerformLayout();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion
    }
}