resource "yandex_iam_service_account" "sa" {
  name = var.name
}

resource "yandex_resourcemanager_folder_iam_member" "sa_roles" {
  for_each = toset(var.roles)

  folder_id = var.provider_config.folder_id
  role      = each.key
  member    = "serviceAccount:${yandex_iam_service_account.sa.id}"
}
