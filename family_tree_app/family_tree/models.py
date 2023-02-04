from django.db import models


class Member(models.Model):
    text = models.CharField(max_length=200)
    id = models.AutoField(primary_key=True)

    def __str__(self):
        return self.text


class Identification(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class Name(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)


class Gender(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class ProfilePhoto(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class FatherID(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='father')


class MotherID(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='mother')


class SpouseID(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class EmailAddress(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)


class ContactNumber(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class PhysicalAddress(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)


class Bio(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class URLforStorage(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)